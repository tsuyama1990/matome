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
                    Currently, only 'gmm' is supported for `clustering_algorithm`.
        """
        self.config = config

        # Validate algorithm
        if config.clustering_algorithm != "gmm":
            # But spec mentioned 'agglomerative' as future possibility.
            # For now, strict validation:
            msg = f"Unsupported clustering algorithm: {config.clustering_algorithm}. Only 'gmm' is supported."
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

        n_samples = len(chunks)

        # Edge case: Single chunk or very few chunks
        if n_samples == 1:
            return [Cluster(id=0, level=0, node_indices=[0])]

        # Adjust n_neighbors for small datasets
        effective_n_neighbors = min(n_neighbors, n_samples - 1)
        effective_n_neighbors = max(effective_n_neighbors, 2) # Minimum viable for UMAP?

        if effective_n_neighbors != n_neighbors:
            logger.warning(
                f"Adjusted UMAP n_neighbors from {n_neighbors} to {effective_n_neighbors} "
                f"due to small dataset size ({n_samples} samples)."
            )

        # 1. Dimensionality Reduction (UMAP)
        # Reduce to 2 dimensions for GMM as per spec
        # UMAP is generally batch-oriented.
        reducer = UMAP(
            n_neighbors=effective_n_neighbors,
            min_dist=min_dist,
            n_components=2,
            random_state=self.config.random_state,  # Use config
        )
        reduced_embeddings = reducer.fit_transform(embeddings)

        # 2. GMM Clustering
        # Find optimal clusters if n_clusters not set in config
        if self.config.n_clusters:
            n_components = self.config.n_clusters
        else:
            n_components = self._calculate_optimal_clusters(reduced_embeddings)

        gmm = GaussianMixture(n_components=n_components, random_state=self.config.random_state)
        gmm.fit(reduced_embeddings)
        labels = gmm.predict(reduced_embeddings)

        # 3. Form Clusters
        clusters = []
        unique_labels = np.unique(labels)
        for label in unique_labels:
            indices = np.where(labels == label)[0]
            # Convert numpy int64 to python int
            node_indices: list[int | str] = [int(i) for i in indices]

            cluster = Cluster(
                id=int(label),
                level=0,  # Assuming level 0 for initial chunks
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
            gmm = GaussianMixture(n_components=n, random_state=self.config.random_state)
            gmm.fit(embeddings)
            bics.append(gmm.bic(embeddings))

        # Find n with minimum BIC
        optimal_n = n_range[np.argmin(bics)]
        return int(optimal_n)
