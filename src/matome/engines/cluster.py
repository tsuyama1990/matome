import contextlib
import logging
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import IncrementalPCA
from sklearn.mixture import GaussianMixture
from umap import UMAP

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from domain_models.manifest import Cluster
from domain_models.types import NodeID
from matome.utils.compat import batched

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
        self, embeddings: Iterable[list[float]], config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Clusters the nodes based on their embeddings.

        Args:
            embeddings: An iterable of vectors (list of floats).
            config: Processing configuration.

        Returns:
            A list of Cluster objects containing indices of grouped nodes.
        """
        self._validate_algorithm(config)

        # Batch size for disk writing to reduce I/O overhead
        WRITE_BATCH_SIZE = config.write_batch_size

        # Create temp file for memory mapping
        fd, tf_name = tempfile.mkstemp()
        os.close(fd)
        path_obj = Path(tf_name)

        try:
            # Stream write embeddings to disk.
            # This ensures we never hold the full list of embeddings in Python memory.
            n_samples, dim = self._stream_write_embeddings(embeddings, path_obj, WRITE_BATCH_SIZE)

            if n_samples == 0:
                return []

            # Handle edge cases (small datasets)
            edge_case_result = self._handle_edge_cases(n_samples)
            if edge_case_result:
                return edge_case_result

            # Open as memmap
            # This allows us to access the data as if it were in memory, backed by disk
            mm_array = np.memmap(tf_name, dtype="float32", mode="r", shape=(n_samples, dim))

            try:
                if n_samples > config.large_scale_threshold:
                    return self._perform_approximate_clustering(mm_array, n_samples, config)

                return self._perform_clustering(mm_array, n_samples, config)
            finally:
                # Ensure memmap is closed/deleted from python view
                del mm_array

        finally:
            if path_obj.exists():
                with contextlib.suppress(OSError):
                    path_obj.unlink()

    def _stream_write_embeddings(
        self, embeddings: Iterable[list[float]], path_obj: Path, batch_size: int
    ) -> tuple[int, int]:
        """
        Stream embeddings to disk in batches.
        Returns (n_samples, dim).
        """
        n_samples = 0
        dim = 0

        with path_obj.open("wb") as f:
            # Use batched utility to iterate in chunks
            # batched() consumes the iterator lazily, ensuring we only hold 'batch_size' items in RAM.
            for batch_tuple in batched(embeddings, batch_size):
                # Process in smaller sub-batches to avoid large memory allocation
                # even if batch_size is large (e.g. from default config).
                # 1000 rows * 1024 dims * 4 bytes = 4MB. Safe.
                SUB_BATCH_SIZE = 1000

                for i in range(0, len(batch_tuple), SUB_BATCH_SIZE):
                    sub_batch = batch_tuple[i : i + SUB_BATCH_SIZE]

                    if n_samples == 0 and i == 0:
                        dim = len(sub_batch[0])
                        if dim == 0:
                            msg = "Embedding dimension cannot be zero."
                            raise ValueError(msg)

                    try:
                        np_batch = np.array(sub_batch, dtype="float32")
                    except ValueError as e:
                        msg = f"Failed to create batch array: {e}"
                        raise ValueError(msg) from e

                    if np_batch.shape[1] != dim:
                        msg = f"Embedding dimension mismatch in batch starting at {n_samples}."
                        raise ValueError(msg)

                    if not np.isfinite(np_batch).all():
                        msg = "Embeddings contain NaN or Infinity values."
                        raise ValueError(msg)

                    np_batch.tofile(f)
                    n_samples += len(sub_batch)

        return n_samples, dim

    def _validate_algorithm(self, config: ProcessingConfig) -> None:
        """Validate that the configured algorithm is supported."""
        algo = config.clustering_algorithm
        # Handle case where it's an Enum (normal) or a raw string (testing/bypassing validation)
        algo_value = algo.value if hasattr(algo, "value") else algo

        # Use the Enum value for validation, avoiding hardcoded string if possible
        expected_algo = ClusteringAlgorithm.GMM.value

        if algo_value != expected_algo:
            msg = f"Unsupported clustering algorithm: {algo}. Only '{expected_algo}' is supported."
            raise ValueError(msg)

    def _handle_edge_cases(self, n_samples: int) -> list[Cluster] | None:
        """
        Handle cases where the dataset is too small for meaningful clustering.

        Returns:
            List of Clusters if handled, None otherwise (proceed to normal clustering).
        """
        if n_samples == 1:
            return [Cluster(id=0, level=0, node_indices=[0])]

        # Threshold for "too small to cluster"
        # Standard UMAP/GMM can fail or be unstable with very few samples.
        # 5 is a reasonable heuristic.
        if n_samples <= 5:
            logger.info(
                f"Dataset too small for clustering ({n_samples} samples). Grouping all into one cluster."
            )
            return [Cluster(id=0, level=0, node_indices=list(range(n_samples)))]

        return None

    def _perform_clustering(
        self, data: np.ndarray, n_samples: int, config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Execute UMAP reduction and GMM clustering on the data.

        Args:
            data: The dataset (numpy array or memmap).
            n_samples: Number of samples.
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
            labels = gmm.predict(reduced_embeddings)

            # 3. Form Clusters
            return self._form_clusters(labels)

        except Exception as e:
            logger.exception("Clustering process failed during UMAP/GMM execution.")
            msg = f"Clustering failed: {e}"
            raise RuntimeError(msg) from e

    def _form_clusters(self, labels: np.ndarray) -> list[Cluster]:
        """Convert clustering labels into Cluster objects."""
        clusters: list[Cluster] = []
        unique_labels = np.unique(labels)
        for label in unique_labels:
            indices = np.where(labels == label)[0]
            # Convert numpy indices to NodeID (int) list
            node_indices: list[NodeID] = [int(idx) for idx in indices]

            cluster = Cluster(
                id=int(label),
                level=0,  # Default to 0, caller handles level logic
                node_indices=node_indices,
            )
            clusters.append(cluster)
        return clusters

    def _perform_approximate_clustering(
        self, data: np.ndarray, n_samples: int, config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Execute streaming clustering using IncrementalPCA and MiniBatchKMeans.
        Avoids loading the entire dataset into memory.
        """
        n_components = config.umap_n_components
        # Use config.n_clusters or heuristic.
        # For large data, we definitely need > 1 cluster.
        # Heuristic: sqrt(n_samples/2) is common, but capped.
        # Or simple constant. Let's default to a reasonable number if not set.
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
            # We can't store all labels in memory if n_samples is huge?
            # 10M labels (int32) is 40MB. That's fine.
            labels_list = []
            for i in range(0, n_samples, batch_size):
                batch = data[i : i + batch_size]
                reduced_batch = ipca.transform(batch)
                batch_labels = kmeans.predict(reduced_batch)
                labels_list.append(batch_labels)

            labels = np.concatenate(labels_list)
            return self._form_clusters(labels)

        except Exception as e:
            logger.exception("Approximate clustering failed.")
            msg = f"Approximate clustering failed: {e}"
            raise RuntimeError(msg) from e

    def _calculate_optimal_clusters(self, embeddings: np.ndarray, random_state: int) -> int:
        """
        Helper to find optimal number of clusters using BIC (Bayesian Information Criterion).
        """
        # Limit max clusters to avoid overfitting or excessive fragmentation.
        # 20 is a heuristic upper bound often sufficient for typical document sectioning tasks.
        # If the number of embeddings is small, we cap it at len(embeddings).
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
            return 1
