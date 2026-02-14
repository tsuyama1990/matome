import contextlib
import logging
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import BinaryIO

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import IncrementalPCA
from sklearn.mixture import GaussianMixture
from umap import UMAP

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from domain_models.manifest import Cluster
from domain_models.types import NodeID

logger = logging.getLogger(__name__)


class GMMClusterer:
    """
    Engine for clustering text chunks/nodes using UMAP and GMM.
    Implements the Clusterer protocol.

    Uses memory mapping to handle large datasets without loading everything into RAM.
    While UMAP/GMM require the full dataset structure for global optimization,
    np.memmap allows the OS to handle paging efficiently, preventing OOM on the Python side.
    """

    def cluster_nodes(
        self, embeddings: Iterable[tuple[NodeID, list[float]]], config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Clusters the nodes based on their embeddings.

        Args:
            embeddings: An iterable of (NodeID, vector) tuples.
            config: Processing configuration.

        Returns:
            A list of Cluster objects containing indices of grouped nodes.
        """
        self._validate_algorithm(config)

        # Batch size for disk writing (from config)
        write_batch_size = config.write_batch_size

        # Create temp file for memory mapping
        fd, tf_name = tempfile.mkstemp()
        os.close(fd)
        path_obj = Path(tf_name)

        try:
            # Stream write embeddings to disk and capture IDs.
            # IDs are stored in memory (list[NodeID]) as they are relatively small.
            # 1 million UUIDs ~ 36MB RAM.
            # This ensures we never hold the full list of embeddings in Python memory.
            n_samples, dim, node_ids = self._stream_write_embeddings(embeddings, path_obj, write_batch_size)

            if n_samples == 0:
                return []

            # Handle edge cases (small datasets)
            edge_case_result = self._handle_edge_cases(n_samples, node_ids)
            if edge_case_result:
                return edge_case_result

            # Open as memmap
            # This allows us to access the data as if it were in memory, backed by disk
            mm_array = np.memmap(tf_name, dtype="float32", mode="r", shape=(n_samples, dim))

            try:
                if n_samples > config.large_scale_threshold:
                    return self._perform_approximate_clustering(mm_array, n_samples, node_ids, config)

                return self._perform_clustering(mm_array, n_samples, node_ids, config)
            finally:
                # Ensure memmap is closed/deleted from python view
                del mm_array

        finally:
            if path_obj.exists():
                with contextlib.suppress(OSError):
                    path_obj.unlink()

    def _stream_write_embeddings(
        self,
        embeddings: Iterable[tuple[NodeID, list[float]]],
        path_obj: Path,
        batch_size: int
    ) -> tuple[int, int, list[NodeID]]:
        """
        Stream embeddings to disk in batches and collect IDs.

        Iterates over the input embeddings and writes them to a binary file
        (to be used with np.memmap). Validates dimensions and values.
        Optimized to write using a configurable buffer to avoid I/O bottlenecks.

        Args:
            embeddings: Iterable of (NodeID, embedding vector).
            path_obj: Path object to write the embeddings to.
            batch_size: Number of embeddings to process at once.

        Returns:
            A tuple (n_samples, dim, node_ids).
        """
        n_samples = 0
        dim = 0
        buffer: list[list[float]] = []
        node_ids: list[NodeID] = []

        # Use configured batch size
        buffer_size = batch_size

        with path_obj.open("wb") as f:
            for i, (nid, vec) in enumerate(embeddings):
                if n_samples == 0 and len(buffer) == 0:
                    dim = len(vec)
                    if dim == 0:
                        msg = "Embedding dimension cannot be zero."
                        raise ValueError(msg)

                if len(vec) != dim:
                    msg = f"Embedding dimension mismatch at index {i}."
                    raise ValueError(msg)

                buffer.append(vec)
                node_ids.append(nid)

                if len(buffer) >= buffer_size:
                    self._flush_buffer(f, buffer)
                    n_samples += len(buffer)
                    buffer.clear()

            # Final flush
            if buffer:
                self._flush_buffer(f, buffer)
                n_samples += len(buffer)
                buffer.clear()

        return n_samples, dim, node_ids

    def _flush_buffer(self, f: BinaryIO, buffer: list[list[float]]) -> None:
        """Helper to write a buffer of vectors to disk."""
        try:
            # Convert whole buffer to array at once - fast
            np_batch = np.array(buffer, dtype="float32")
        except ValueError as e:
            msg = f"Failed to create array from buffer: {e}"
            raise ValueError(msg) from e

        if not np.isfinite(np_batch).all():
            msg = "Embeddings contain NaN or Infinity values."
            raise ValueError(msg)

        np_batch.tofile(f)

    def _validate_algorithm(self, config: ProcessingConfig) -> None:
        """Validate that the configured algorithm is supported."""
        algo = config.clustering_algorithm
        # Strict Enum comparison
        if algo != ClusteringAlgorithm.GMM:
            msg = f"Unsupported clustering algorithm: {algo}. Only '{ClusteringAlgorithm.GMM.value}' is supported."
            raise ValueError(msg)

    def _handle_edge_cases(self, n_samples: int, node_ids: list[NodeID]) -> list[Cluster] | None:
        """
        Handle cases where the dataset is too small for meaningful clustering.

        Checks if the number of samples is below a minimum threshold for
        clustering algorithms (UMAP/GMM) to work reliably.

        Args:
            n_samples: The number of embedding samples.
            node_ids: List of Node IDs corresponding to samples.

        Returns:
            List of Clusters if handled (e.g., single cluster),
            None otherwise (indicating to proceed to normal clustering).
        """
        if n_samples == 1:
            return [Cluster(id=0, level=0, node_indices=[node_ids[0]])]

        # Threshold for "too small to cluster"
        # Standard UMAP/GMM can fail or be unstable with very few samples.
        # 5 is a reasonable heuristic.
        if n_samples <= 5:
            logger.info(
                f"Dataset too small for clustering ({n_samples} samples). Grouping all into one cluster."
            )
            return [Cluster(id=0, level=0, node_indices=node_ids)]

        return None

    def _perform_clustering(
        self, data: np.ndarray, n_samples: int, node_ids: list[NodeID], config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Execute UMAP reduction and GMM clustering on the data.
        Performs Soft Clustering using GMM probabilities.

        Args:
            data: The dataset (numpy array or memmap).
            n_samples: Number of samples.
            node_ids: List of Node IDs corresponding to data indices.
            config: Configuration object.

        Returns:
            List of resulting Cluster objects.
        """
        # UMAP Parameters
        n_neighbors = config.umap_n_neighbors
        min_dist = config.umap_min_dist
        n_components = config.umap_n_components

        # Adjust n_neighbors if dataset is small but larger than edge case threshold
        effective_n_neighbors = max(min(n_neighbors, n_samples - 1), 2)

        if effective_n_neighbors != n_neighbors:
            logger.warning(
                f"Adjusted UMAP n_neighbors from {n_neighbors} to {effective_n_neighbors} "
                f"due to small dataset size ({n_samples} samples)."
            )

        logger.info(
            f"Starting clustering for {n_samples} nodes. "
            f"UMAP params: neighbors={effective_n_neighbors}, min_dist={min_dist}. "
            f"GMM target: {config.n_clusters if config.n_clusters else 'auto-BIC'}."
        )

        try:
            # 1. Dimensionality Reduction (UMAP)
            logger.debug("Running UMAP dimensionality reduction...")
            reducer = UMAP(
                n_neighbors=effective_n_neighbors,
                min_dist=min_dist,
                n_components=n_components,
                random_state=config.random_state,
            )
            reduced_embeddings = reducer.fit_transform(data)

            # 2. GMM Clustering
            if config.n_clusters:
                gmm_n_components = config.n_clusters
            else:
                logger.debug("Calculating optimal cluster count using BIC...")
                gmm_n_components = self._calculate_optimal_clusters(
                    reduced_embeddings, config.random_state
                )

            logger.info(f"Clustering into {gmm_n_components} components.")
            gmm = GaussianMixture(n_components=gmm_n_components, random_state=config.random_state)
            gmm.fit(reduced_embeddings)

            # 3. Soft Clustering (Probabilistic Assignment)
            probs = gmm.predict_proba(reduced_embeddings)
            return self._form_clusters_soft(
                probs, gmm_n_components, config.clustering_probability_threshold, node_ids
            )

        except Exception as e:
            logger.exception("Clustering process failed during UMAP/GMM execution.")
            msg = f"Clustering failed: {e}"
            raise RuntimeError(msg) from e

    def _form_clusters(self, labels: np.ndarray, node_ids: list[NodeID]) -> list[Cluster]:
        """Convert hard clustering labels into Cluster objects (used for approx clustering)."""
        clusters: list[Cluster] = []
        unique_labels = np.unique(labels)
        for label in unique_labels:
            indices = np.where(labels == label)[0]

            # Map indices to NodeIDs
            mapped_ids: list[NodeID] = [node_ids[i] for i in indices]

            cluster = Cluster(
                id=int(label),
                level=0,  # Default to 0, caller handles level logic
                node_indices=mapped_ids,
            )
            clusters.append(cluster)
        return clusters

    def _form_clusters_soft(
        self, probs: np.ndarray, n_clusters: int, threshold: float, node_ids: list[NodeID]
    ) -> list[Cluster]:
        """
        Convert GMM probabilities into Cluster objects (Soft Clustering).
        A node is assigned to a cluster if P(cluster|node) >= threshold.
        Guarantees every node is assigned to at least one cluster (argmax).
        """
        # Dictionary to hold list of node IDs for each cluster
        cluster_map: dict[int, list[NodeID]] = {i: [] for i in range(n_clusters)}

        n_samples = probs.shape[0]

        for i in range(n_samples):
            # Get probabilities for node i
            node_probs = probs[i]
            nid = node_ids[i]

            # Identify clusters exceeding threshold
            assigned_indices = np.where(node_probs >= threshold)[0]

            # If no cluster exceeds threshold, assign to the one with max probability
            if len(assigned_indices) == 0:
                max_idx = np.argmax(node_probs)
                cluster_map[int(max_idx)].append(nid)
            else:
                for cluster_idx in assigned_indices:
                    cluster_map[int(cluster_idx)].append(nid)

        # Create Cluster objects
        clusters: list[Cluster] = []
        for cluster_id, mapped_ids in cluster_map.items():
            if mapped_ids:
                clusters.append(Cluster(id=cluster_id, level=0, node_indices=mapped_ids))

        return clusters

    def _perform_approximate_clustering(
        self, data: np.ndarray, n_samples: int, node_ids: list[NodeID], config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Execute streaming clustering using IncrementalPCA and MiniBatchKMeans.
        Avoids loading the entire dataset into memory.
        """
        n_components = config.umap_n_components
        # Use config.n_clusters or heuristic.
        n_clusters = config.n_clusters or min(int(np.sqrt(n_samples)), 50)

        logger.info(
            f"Starting Approximate Clustering for {n_samples} nodes. "
            f"PCA components={n_components}, KMeans clusters={n_clusters}."
        )

        try:
            # 1. Incremental PCA Training
            ipca = IncrementalPCA(n_components=n_components)
            batch_size = config.write_batch_size  # reuse batch size

            # Loop over memmap in batches
            for i in range(0, n_samples, batch_size):
                batch = data[i : i + batch_size]
                ipca.partial_fit(batch)

            # 2. MiniBatchKMeans Training
            # We must transform and feed to KMeans
            kmeans = MiniBatchKMeans(
                n_clusters=n_clusters,
                random_state=config.random_state,
                batch_size=batch_size,
                n_init="auto",
            )

            for i in range(0, n_samples, batch_size):
                batch = data[i : i + batch_size]
                reduced_batch = ipca.transform(batch)
                kmeans.partial_fit(reduced_batch)

            # 3. Predict Labels (Final Pass)
            labels_list = []
            for i in range(0, n_samples, batch_size):
                batch = data[i : i + batch_size]
                reduced_batch = ipca.transform(batch)
                batch_labels = kmeans.predict(reduced_batch)
                labels_list.append(batch_labels)

            labels = np.concatenate(labels_list)
            return self._form_clusters(labels, node_ids)

        except Exception as e:
            logger.exception("Approximate clustering failed.")
            msg = f"Approximate clustering failed: {e}"
            raise RuntimeError(msg) from e

    def _calculate_optimal_clusters(self, embeddings: np.ndarray, random_state: int) -> int:
        """
        Helper to find optimal number of clusters using BIC (Bayesian Information Criterion).
        """
        # Limit max clusters to avoid overfitting or excessive fragmentation.
        max_clusters = min(20, len(embeddings))

        if max_clusters < 2:
            return 1

        bics = []
        n_range = range(2, max_clusters + 1)

        try:
            for n in n_range:
                gmm = GaussianMixture(n_components=n, random_state=random_state)
                gmm.fit(embeddings)
                bics.append(gmm.bic(embeddings))

            if not bics:
                return 1

            # Find n with minimum BIC
            optimal_n = n_range[np.argmin(bics)]
            return int(optimal_n)

        except (ValueError, RuntimeError) as e:
            # Catch specific errors like convergence failure
            logger.warning(f"Error during BIC calculation: {e!s}. Defaulting to 1 cluster.")
            return 1
        except Exception:
            # Catch import errors or other unexpected issues
            logger.exception("Unexpected error during BIC calculation. Defaulting to 1 cluster.")
            raise
