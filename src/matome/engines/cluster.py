import logging
from collections.abc import Iterable

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
        embeddings: Iterable[list[float]],
        config: ProcessingConfig
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

        # Materialize iterator to check size and content
        embeddings_list = list(embeddings)
        n_samples = len(embeddings_list)

        if n_samples == 0:
            return []

        # Validate dimensions and content
        # Check first element for dimension
        dim = len(embeddings_list[0])
        if dim == 0:
            msg = "Embedding dimension cannot be zero."
            raise ValueError(msg)

        # Check all
        for i, emb in enumerate(embeddings_list):
            if len(emb) != dim:
                msg = f"Embedding dimension mismatch at index {i}."
                raise ValueError(msg)
            if any(np.isnan(x) or np.isinf(x) for x in emb):
                msg = "Embeddings contain NaN or Infinity values."
                raise ValueError(msg)

        # Handle edge cases (small datasets)
        edge_case_result = self._handle_edge_cases(n_samples)
        if edge_case_result:
            return edge_case_result

        # Convert to numpy array for processing
        data = np.array(embeddings_list, dtype='float32')

        return self._perform_clustering(data, n_samples, config)

    def _validate_algorithm(self, config: ProcessingConfig) -> None:
        algo = config.clustering_algorithm
        # Handle case where it's an Enum (normal) or a raw string (testing/bypassing validation)
        algo_value = algo.value if hasattr(algo, "value") else algo

        if algo_value != "gmm":
            msg = f"Unsupported clustering algorithm: {algo}. Only 'gmm' is supported."
            raise ValueError(msg)

    def _handle_edge_cases(self, n_samples: int) -> list[Cluster] | None:
        """
        Handle cases where the dataset is too small for meaningful clustering.
        """
        if n_samples == 1:
            return [Cluster(id=0, level=0, node_indices=[0])]

        # Threshold for "too small to cluster"
        # Standard UMAP/GMM can fail or be unstable with very few samples.
        # 5 is a reasonable heuristic.
        if n_samples <= 5:
            logger.info(f"Dataset too small for clustering ({n_samples} samples). Grouping all into one cluster.")
            return [Cluster(id=0, level=0, node_indices=list(range(n_samples)))]

        return None

    def _perform_clustering(self, data: np.ndarray, n_samples: int, config: ProcessingConfig) -> list[Cluster]:
        """Helper to run UMAP and GMM on the data."""
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
                gmm_n_components = self._calculate_optimal_clusters(reduced_embeddings, config.random_state)

            logger.info(f"Clustering into {gmm_n_components} components.")
            gmm = GaussianMixture(n_components=gmm_n_components, random_state=config.random_state)
            gmm.fit(reduced_embeddings)
            labels = gmm.predict(reduced_embeddings)

            # 3. Form Clusters
            return self._form_clusters(labels)

        except Exception:
            logger.exception("Clustering failed.")
            raise

    def _form_clusters(self, labels: np.ndarray) -> list[Cluster]:
        clusters: list[Cluster] = []
        unique_labels = np.unique(labels)
        for label in unique_labels:
            indices = np.where(labels == label)[0]
            # Convert numpy indices to NodeID (int) list
            node_indices: list[NodeID] = [int(idx) for idx in indices]

            cluster = Cluster(
                id=int(label),
                level=0, # Default to 0, caller handles level logic
                node_indices=node_indices,
            )
            clusters.append(cluster)
        return clusters

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
