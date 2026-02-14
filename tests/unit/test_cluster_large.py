from unittest.mock import MagicMock, patch
import tempfile
from pathlib import Path

import numpy as np
import pytest

from domain_models.config import ProcessingConfig
from matome.engines.cluster import GMMClusterer


def test_approximate_clustering_path() -> None:
    """
    Test that the clustering path runs IncrementalPCA + MiniBatchKMeans.
    """
    config = ProcessingConfig(
        n_clusters=2, random_state=42, write_batch_size=10, umap_n_components=2
    )

    clusterer = GMMClusterer()

    data = np.random.rand(30, 10).astype("float32")

    # Create temporary file for IDs
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        # Write 30 IDs
        f.write("\n".join([str(i) for i in range(30)]) + "\n")
        path_ids = Path(f.name)

    try:
        with (
            patch("matome.engines.cluster.IncrementalPCA") as MockIPCA,
            patch("matome.engines.cluster.MiniBatchKMeans") as MockKMeans,
        ):
            mock_ipca = MockIPCA.return_value
            mock_kmeans = MockKMeans.return_value

            # Setup mocks
            # transform returns array of shape (batch_size, n_components)
            mock_ipca.transform.side_effect = lambda x: np.random.rand(len(x), 2)

            # predict returns labels for batch
            mock_kmeans.predict.side_effect = lambda x: np.array([0, 1] * (len(x) // 2))

            # _perform_clustering(data, n_samples, path_ids, config)
            clusters = clusterer._perform_clustering(data, 30, path_ids, config)

            assert MockIPCA.called
            assert MockKMeans.called
            assert len(clusters) > 0

            # Verify partial_fit calls
            # batch_size=10, n_samples=30 -> 3 batches
            assert mock_ipca.partial_fit.call_count == 3
            assert mock_kmeans.partial_fit.call_count == 3
            assert mock_kmeans.predict.call_count == 3
    finally:
        path_ids.unlink()
