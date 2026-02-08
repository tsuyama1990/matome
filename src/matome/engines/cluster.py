import logging

import numpy as np
from sklearn.mixture import GaussianMixture
from umap import UMAP

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster

logger = logging.getLogger(__name__)

class ClusterEngine:
    """Engine for clustering text chunks using UMAP and GMM."""

    def __init__(self, config: ProcessingConfig) -> None:
        """
        Initialize the clustering engine.

        Args:
            config: Processing configuration containing clustering parameters.
                    Currently, only 'gmm' is supported for `clustering.algorithm`.
        """
        self.config = config

        # Validate algorithm
        if config.clustering.algorithm != "gmm":
            msg = f"Unsupported clustering algorithm: {config.clustering.algorithm}. Only 'gmm' is supported."
            raise ValueError(msg)

    def perform_clustering(
        self,
        chunks: list[Chunk],
        embeddings: np.ndarray,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
    ) -> list[Cluster]:
        """
        Clusters the chunks based on their embeddings.

        Args:
            chunks: The list of chunks (used for indices).
            embeddings: The numpy array of embeddings corresponding to chunks.
            n_neighbors: UMAP parameter for local neighborhood size.
                         Will be automatically adjusted if larger than dataset size.
            min_dist: UMAP parameter for minimum distance between points.

        Returns:
            A list of Cluster objects containing indices of grouped chunks.
        """
        if not chunks:
            return []

        # Input Validation
        if embeddings.size == 0:
            logger.warning("Empty embeddings array provided to clustering.")
            return []

        if np.isnan(embeddings).any() or np.isinf(embeddings).any():
            msg = "Embeddings contain NaN or Infinity values."
            raise ValueError(msg)

        n_samples = len(chunks)

        # Edge case: Single chunk
        if n_samples == 1:
            return [Cluster(id=0, level=0, node_indices=[chunks[0].index])]

        # Edge case: Very small dataset (< 3 samples).
        if n_samples < 3:
            logger.info(f"Dataset too small for clustering ({n_samples} samples). Grouping all into one cluster.")
            return [Cluster(id=0, level=0, node_indices=[c.index for c in chunks])]

        # Adjust n_neighbors for small datasets
        effective_n_neighbors = min(n_neighbors, n_samples - 1)
        effective_n_neighbors = max(effective_n_neighbors, 2) # Minimum viable for UMAP?

        if effective_n_neighbors != n_neighbors:
            logger.warning(
                f"Adjusted UMAP n_neighbors from {n_neighbors} to {effective_n_neighbors} "
                f"due to small dataset size ({n_samples} samples)."
            )

        logger.debug(
            f"Starting clustering with {n_samples} samples. "
            f"UMAP: n_neighbors={effective_n_neighbors}, min_dist={min_dist}. "
            f"GMM: n_clusters={self.config.clustering.n_clusters or 'auto'}."
        )

        # 1. Dimensionality Reduction (UMAP)
        reducer = UMAP(
            n_neighbors=effective_n_neighbors,
            min_dist=min_dist,
            n_components=2,
            random_state=self.config.clustering.random_state,
        )
        reduced_embeddings = reducer.fit_transform(embeddings)

        # 2. GMM Clustering
        if self.config.clustering.n_clusters:
            n_components = self.config.clustering.n_clusters
        else:
            n_components = self._calculate_optimal_clusters(reduced_embeddings)

        gmm = GaussianMixture(n_components=n_components, random_state=self.config.clustering.random_state)
        gmm.fit(reduced_embeddings)
        labels = gmm.predict(reduced_embeddings)

        # 3. Form Clusters
        clusters = []
        unique_labels = np.unique(labels)
        for label in unique_labels:
            indices = np.where(labels == label)[0]
            # Robust type conversion using .item()
            node_indices: list[int | str] = [int(indices[i].item()) for i in range(len(indices))]

            cluster = Cluster(
                id=int(label.item()) if hasattr(label, "item") else int(label),
                level=0,
                node_indices=node_indices,
            )
            clusters.append(cluster)

        return clusters

    def _calculate_optimal_clusters(self, embeddings: np.ndarray) -> int:
        """
        Helper to find optimal number of clusters using BIC (Bayesian Information Criterion).

        Args:
            embeddings: The reduced embeddings (2D).

        Returns:
            Optimal number of clusters.
        """
        max_clusters = min(20, len(embeddings))
        if max_clusters < 2:
            return 1

        bics = []
        n_range = range(2, max_clusters + 1)
        for n in n_range:
            gmm = GaussianMixture(n_components=n, random_state=self.config.clustering.random_state)
            gmm.fit(embeddings)
            bics.append(gmm.bic(embeddings))

        # Find n with minimum BIC
        optimal_n = n_range[np.argmin(bics)]
        return int(optimal_n)
