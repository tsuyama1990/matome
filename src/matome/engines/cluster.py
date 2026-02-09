import logging
import tempfile
from pathlib import Path

import numpy as np
from sklearn.mixture import GaussianMixture
from umap import UMAP

from domain_models.config import ProcessingConfig
from domain_models.manifest import Cluster
from domain_models.types import NodeID

logger = logging.getLogger(__name__)

class GMMClusterer:
    """
    Engine for clustering text chunks/nodes using UMAP and GMM.
    Implements the Clusterer protocol.
    """

    def cluster_nodes(
        self,
        embeddings: list[list[float]],
        config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Clusters the nodes based on their embeddings.

        Args:
            embeddings: A list of vectors (list of floats).
            config: Processing configuration.

        Returns:
            A list of Cluster objects containing indices of grouped nodes.
        """
        if not embeddings:
            return []

        self._validate_algorithm(config)
        self._validate_embeddings(embeddings)

        n_samples = len(embeddings)
        if n_samples == 0:
            return []

        # Handle edge cases (n < 3) separately
        edge_case_result = self._handle_edge_cases(n_samples)
        if edge_case_result:
            return edge_case_result

        # Use memory-mapped file for main processing
        return self._process_with_memmap(embeddings, n_samples, config)

    def _validate_algorithm(self, config: ProcessingConfig) -> None:
        if config.clustering_algorithm != "gmm":
            msg = f"Unsupported clustering algorithm: {config.clustering_algorithm}. Only 'gmm' is supported."
            raise ValueError(msg)

    def _validate_embeddings(self, embeddings: list[list[float]]) -> None:
        if any(e is None for e in embeddings):
             msg = "Embeddings list contains None values."
             raise ValueError(msg)

        # Check for NaN/Inf in small datasets where memmap is skipped
        if len(embeddings) < 3:
             for vec in embeddings:
                 if any(np.isnan(x) or np.isinf(x) for x in vec):
                      msg = "Embeddings contain NaN or Infinity values."
                      raise ValueError(msg)

    def _handle_edge_cases(self, n_samples: int) -> list[Cluster] | None:
        if n_samples == 1:
            return [Cluster(id=0, level=0, node_indices=[0])]

        if n_samples <= 5:
            logger.info(f"Dataset too small for clustering ({n_samples} samples). Grouping all into one cluster.")
            return [Cluster(id=0, level=0, node_indices=list(range(n_samples)))]

        return None

    def _process_with_memmap(self, embeddings: list[list[float]], n_samples: int, config: ProcessingConfig) -> list[Cluster]:
        dim = len(embeddings[0])

        # Use context manager to satisfy SIM115
        # delete=False ensures file persists after close for memmap usage
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf_name = tf.name

        try:
            mm_array = np.memmap(tf_name, dtype='float32', mode='w+', shape=(n_samples, dim))

            # Copy data
            for i, emb in enumerate(embeddings):
                mm_array[i] = emb

            mm_array.flush()

            # Validate content on memmap
            if np.isnan(mm_array).any() or np.isinf(mm_array).any():
                 msg = "Embeddings contain NaN or Infinity values."
                 raise ValueError(msg)

            # Perform clustering
            clusters = self._perform_clustering(mm_array, n_samples, config)

            # Ensure memmap is closed/deleted before unlinking file
            del mm_array
            return clusters

        finally:
            # Manual cleanup of temporary file using Path (PTH110, PTH108)
            path = Path(tf_name)
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    logger.warning(f"Failed to delete temporary file: {tf_name}")

    def _perform_clustering(self, data: np.ndarray, n_samples: int, config: ProcessingConfig) -> list[Cluster]:
        """Helper to run UMAP and GMM on the data (numpy array or memmap)."""
        # UMAP Parameters
        n_neighbors = config.umap_n_neighbors
        min_dist = config.umap_min_dist

        effective_n_neighbors = max(min(n_neighbors, n_samples - 1), 2)

        if effective_n_neighbors != n_neighbors:
            logger.warning(
                f"Adjusted UMAP n_neighbors from {n_neighbors} to {effective_n_neighbors} "
                f"due to small dataset size ({n_samples} samples)."
            )

        logger.debug(
            f"Starting clustering with {n_samples} samples. "
            f"UMAP: n_neighbors={effective_n_neighbors}, min_dist={min_dist}. "
            f"GMM: n_clusters={config.n_clusters or 'auto'}."
        )

        # 1. Dimensionality Reduction (UMAP)
        reducer = UMAP(
            n_neighbors=effective_n_neighbors,
            min_dist=min_dist,
            n_components=2,
            random_state=config.random_state,
        )
        reduced_embeddings = reducer.fit_transform(data)

        # 2. GMM Clustering
        if config.n_clusters:
            n_components = config.n_clusters
        else:
            n_components = self._calculate_optimal_clusters(reduced_embeddings, config.random_state)

        gmm = GaussianMixture(n_components=n_components, random_state=config.random_state)
        gmm.fit(reduced_embeddings)
        labels = gmm.predict(reduced_embeddings)

        # 3. Form Clusters
        return self._form_clusters(labels)

    def _form_clusters(self, labels: np.ndarray) -> list[Cluster]:
        clusters: list[Cluster] = []
        unique_labels = np.unique(labels)
        for label in unique_labels:
            indices = np.where(labels == label)[0]
            node_indices: list[NodeID] = [int(indices[i].item()) for i in range(len(indices))]

            cluster = Cluster(
                id=int(label.item()) if hasattr(label, "item") else int(label),
                level=0,
                node_indices=node_indices,
            )
            clusters.append(cluster)
        return clusters

    def _calculate_optimal_clusters(self, embeddings: np.ndarray, random_state: int) -> int:
        """
        Helper to find optimal number of clusters using BIC (Bayesian Information Criterion).
        """
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
                # Should not happen given logic above, but for safety
                return 1

            # Find n with minimum BIC
            optimal_n = n_range[np.argmin(bics)]
            return int(optimal_n)

        except Exception:
            logger.exception("Failed to calculate optimal clusters via BIC. Defaulting to 1.")
            return 1
