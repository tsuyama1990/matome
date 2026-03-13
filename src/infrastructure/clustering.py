import logging
from typing import Any

import numpy as np

from src.interfaces.clustering import ClusteringStrategy

logger = logging.getLogger(__name__)

try:
    import umap.umap_ as umap
    from sklearn.mixture import GaussianMixture

    _ML_IMPORTS_SUCCESSFUL = True
except ImportError:
    _ML_IMPORTS_SUCCESSFUL = False


class UMAPGMMClusteringStrategy(ClusteringStrategy):
    """Clustering strategy using UMAP for dimension reduction and GMM for clustering."""

    def __init__(self) -> None:
        if not _ML_IMPORTS_SUCCESSFUL:
            msg = "Missing required ML dependencies (umap-learn, scikit-learn)."
            raise RuntimeError(msg)

    def _validate_embeddings(self, embeddings: list[list[float]]) -> np.ndarray:
        arr = np.array(embeddings, dtype=np.float32)
        if arr.ndim != 2:
            msg = f"Invalid embedding dimensions. Expected 2D array, got {arr.shape}."
            raise ValueError(msg)
        return arr

    def reduce_dimensions(self, embeddings: list[list[float]]) -> Any:
        arr = self._validate_embeddings(embeddings)
        n_samples = len(arr)

        if n_samples == 0:
            return np.array([])
        if n_samples <= 3:
            # UMAP requires more samples to work properly
            return arr

        n_neighbors = min(15, n_samples - 1)
        n_components = min(arr.shape[1], 10, n_samples - 2)

        try:
            reducer = umap.UMAP(
                n_neighbors=n_neighbors,
                n_components=n_components,
                metric="cosine",
                random_state=42,
            )
            return reducer.fit_transform(arr)
        except Exception as e:
            from sklearn.decomposition import PCA

            if arr.shape[1] > 2:
                pca = PCA(n_components=min(arr.shape[1], 2), random_state=42)
                return pca.fit_transform(arr)
            logger.exception("Failed to reduce embeddings dimensions.")
            msg = "Failed to reduce embeddings dimensions."
            raise RuntimeError(msg) from e

    def cluster(self, embeddings: Any, max_clusters: int) -> dict[int, list[int]]:
        arr = embeddings
        if not isinstance(arr, np.ndarray) or arr.ndim != 2:
            msg = "Invalid embedding dimensions."
            raise ValueError(msg)

        n_samples = len(arr)
        if n_samples == 0 or (n_samples == 1 and arr.shape[1] == 0):
            return {}

        n_clusters = min(max_clusters, n_samples)

        if n_samples < 3 or n_samples <= n_clusters:
            if n_samples == 2:
                return {0: [0], 1: [1]}
            if n_samples == 1:
                return {0: [0]}

        try:
            gmm = GaussianMixture(n_components=n_clusters, random_state=42, n_init=3)
            gmm.fit(arr)
            probs = gmm.predict_proba(arr)

            clusters: dict[int, list[int]] = {i: [] for i in range(n_clusters)}
            threshold = 1.0 / n_clusters

            for i, prob_array in enumerate(probs):
                for cluster_idx, prob in enumerate(prob_array):
                    if prob >= threshold:
                        clusters[cluster_idx].append(i)

            return {k: v for k, v in clusters.items() if v}
        except Exception:
            logger.exception("GMM clustering failed. Falling back to singular cluster.")
            return {0: list(range(n_samples))}
