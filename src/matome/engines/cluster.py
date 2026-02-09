import logging
import tempfile

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
        # Validate algorithm
        if config.clustering_algorithm != "gmm":
            msg = f"Unsupported clustering algorithm: {config.clustering_algorithm}. Only 'gmm' is supported."
            raise ValueError(msg)

        if not embeddings:
            return []

        # Validate data integrity (no None embeddings)
        # Note: Iterating to check integrity is fast enough
        if any(e is None for e in embeddings):
             msg = "Embeddings list contains None values."
             raise ValueError(msg)

        n_samples = len(embeddings)
        if n_samples == 0:
            return []

        dim = len(embeddings[0])

        # Edge case: Single node or small dataset
        # We must check for NaNs/Infs even in these cases if we want strict validation.
        # Since n is small, we can convert to array/memmap and check, or check manually.
        # Let's rely on _perform_clustering validation logic, BUT _perform_clustering
        # is only called for n >= 3 usually.
        # To ensure consistency, we should validate content before returning early results
        # if the test demands it.
        # For n < 3, checking explicitly:
        if n_samples < 3:
             for vec in embeddings:
                 if any(np.isnan(x) or np.isinf(x) for x in vec):
                      msg = "Embeddings contain NaN or Infinity values."
                      raise ValueError(msg)

        # Edge case: Single node
        if n_samples == 1:
            return [Cluster(id=0, level=0, node_indices=[0])]

        # Edge case: Very small dataset (< 3 samples).
        if n_samples < 3:
            logger.info(f"Dataset too small for clustering ({n_samples} samples). Grouping all into one cluster.")
            return [Cluster(id=0, level=0, node_indices=list(range(n_samples)))]

        # Use memory-mapped file to avoid in-memory numpy array copy
        # limiting OOM risk for large datasets

        with tempfile.NamedTemporaryFile(delete=True) as tf:
            # We need a filename for memmap
            # NamedTemporaryFile is deleted on close. We keep it open or use name.
            # On Linux/Unix, we can use the name while open.

            # Create a memmap array matching the shape
            # We use 'w+' to read/write
            mm_array = np.memmap(tf, dtype='float32', mode='w+', shape=(n_samples, dim))

            # Copy data to memmap chunk by chunk or row by row
            # Since input is a list, we iterate.
            for i, emb in enumerate(embeddings):
                mm_array[i] = emb

            # Flush changes to disk
            mm_array.flush()

            # Now perform clustering using the memmap array
            # Cleanup is handled by NamedTemporaryFile context exit
            return self._perform_clustering(mm_array, n_samples, config)

    def _perform_clustering(self, data: np.ndarray, n_samples: int, config: ProcessingConfig) -> list[Cluster]:
        """Helper to run UMAP and GMM on the data (numpy array or memmap)."""

        # Input Validation (checking nan/inf on the array/memmap)
        # This might be expensive on memmap, but necessary.
        if np.isnan(data).any() or np.isinf(data).any():
             msg = "Embeddings contain NaN or Infinity values."
             raise ValueError(msg)

        # UMAP Parameters from Config
        n_neighbors = config.umap_n_neighbors
        min_dist = config.umap_min_dist

        # Adjust n_neighbors for small datasets
        effective_n_neighbors = min(n_neighbors, n_samples - 1)
        effective_n_neighbors = max(effective_n_neighbors, 2)

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
        clusters: list[Cluster] = []
        unique_labels = np.unique(labels)
        for label in unique_labels:
            indices = np.where(labels == label)[0]
            # Convert numpy indices to standard python ints for JSON serializability
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
        for n in n_range:
            gmm = GaussianMixture(n_components=n, random_state=random_state)
            gmm.fit(embeddings)
            bics.append(gmm.bic(embeddings))

        # Find n with minimum BIC
        optimal_n = n_range[np.argmin(bics)]
        return int(optimal_n)
