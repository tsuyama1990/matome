import contextlib
import logging
import os
import tempfile
from collections.abc import Iterable
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

        n_samples = 0
        dim = 0

        # Create temp file
        fd, tf_name = tempfile.mkstemp()
        os.close(fd)

        try:
            # First pass: Write to binary file
            path_obj = Path(tf_name)
            # Use buffering to optimize I/O
            with path_obj.open('wb') as f:
                for i, emb in enumerate(embeddings):
                    if i == 0:
                        dim = len(emb)
                        if dim == 0:
                             msg = "Embedding dimension cannot be zero."
                             raise ValueError(msg)
                    elif len(emb) != dim:
                         msg = f"Embedding dimension mismatch at index {i}."
                         raise ValueError(msg)

                    if any(np.isnan(x) or np.isinf(x) for x in emb):
                         msg = "Embeddings contain NaN or Infinity values."
                         raise ValueError(msg)

                    # tofile writes C-order floats directly
                    np.array(emb, dtype='float32').tofile(f)
                    n_samples += 1

            if n_samples == 0:
                return []

            # Handle edge cases
            edge_case_result = self._handle_edge_cases(n_samples)
            if edge_case_result:
                return edge_case_result

            # Open as memmap
            mm_array = np.memmap(tf_name, dtype='float32', mode='r', shape=(n_samples, dim))

            try:
                return self._perform_clustering(mm_array, n_samples, config)
            finally:
                # Close memmap logic
                del mm_array

        finally:
             # Cleanup
             path = Path(tf_name)
             if path.exists():
                 with contextlib.suppress(OSError):
                     path.unlink()

    def _validate_algorithm(self, config: ProcessingConfig) -> None:
        if config.clustering_algorithm != "gmm":
            msg = f"Unsupported clustering algorithm: {config.clustering_algorithm}. Only 'gmm' is supported."
            raise ValueError(msg)

    def _handle_edge_cases(self, n_samples: int) -> list[Cluster] | None:
        if n_samples == 1:
            return [Cluster(id=0, level=0, node_indices=[0])]

        if n_samples <= 5:
            logger.info(f"Dataset too small for clustering ({n_samples} samples). Grouping all into one cluster.")
            return [Cluster(id=0, level=0, node_indices=list(range(n_samples)))]

        return None

    def _perform_clustering(self, data: np.ndarray, n_samples: int, config: ProcessingConfig) -> list[Cluster]:
        """Helper to run UMAP and GMM on the data (numpy array or memmap)."""
        # UMAP Parameters
        n_neighbors = config.umap_n_neighbors
        min_dist = config.umap_min_dist
        n_components = config.umap_n_components

        effective_n_neighbors = max(min(n_neighbors, n_samples - 1), 2)

        if effective_n_neighbors != n_neighbors:
            logger.warning(
                f"Adjusted UMAP n_neighbors from {n_neighbors} to {effective_n_neighbors} "
                f"due to small dataset size ({n_samples} samples)."
            )

        logger.debug(
            f"Starting clustering with {n_samples} samples. "
            f"UMAP: n_neighbors={effective_n_neighbors}, min_dist={min_dist}, n_components={n_components}. "
            f"GMM: n_clusters={config.n_clusters or 'auto'}."
        )

        # 1. Dimensionality Reduction (UMAP)
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
            gmm_n_components = self._calculate_optimal_clusters(reduced_embeddings, config.random_state)

        gmm = GaussianMixture(n_components=gmm_n_components, random_state=config.random_state)
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
