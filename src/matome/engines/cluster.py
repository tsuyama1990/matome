import logging

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

        # Convert to numpy for processing
        emb_array = np.array(embeddings)

        # Input Validation
        if np.isnan(emb_array).any() or np.isinf(emb_array).any():
            msg = "Embeddings contain NaN or Infinity values."
            raise ValueError(msg)

        n_samples = len(embeddings)

        # Edge case: Single node
        if n_samples == 1:
            return [Cluster(id=0, level=0, node_indices=[0])]

        # Edge case: Very small dataset (< 3 samples).
        if n_samples < 3:
            logger.info(f"Dataset too small for clustering ({n_samples} samples). Grouping all into one cluster.")
            return [Cluster(id=0, level=0, node_indices=list(range(n_samples)))]

        # UMAP Parameters (could be moved to config if needed)
        n_neighbors = 15
        min_dist = 0.1

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
        reduced_embeddings = reducer.fit_transform(emb_array)

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
            # Note: Protocol defines node_indices as relative to the input list
            node_indices: list[NodeID] = [int(indices[i].item()) for i in range(len(indices))]

            cluster = Cluster(
                id=int(label.item()) if hasattr(label, "item") else int(label),
                level=0, # This level is relative to the current operation?
                         # Actually Cluster object has 'level' field.
                         # Usually clustering happens at a specific level.
                         # The Clusterer doesn't know the level of input nodes.
                         # We default to 0 or leave it to caller?
                         # The field is required. Let's set to 0. Caller can update.
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
