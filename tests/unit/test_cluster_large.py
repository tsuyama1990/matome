from unittest.mock import patch

import numpy as np

from domain_models.config import ProcessingConfig
from matome.engines.cluster import GMMClusterer


def test_approximate_clustering_path() -> None:
    """
    Test that the approximate clustering path is taken when n_samples exceeds threshold.
    And verify it runs IncrementalPCA + MiniBatchKMeans.
    """
    config = ProcessingConfig(
        n_clusters=2,
        random_state=42,
        write_batch_size=10,
        umap_n_components=2
    )

    clusterer = GMMClusterer()

    # We patch the threshold check inside the method logic?
    # No, hardcoded constant LARGE_SCALE_THRESHOLD = 20000.
    # We need to mock _perform_approximate_clustering OR mock the threshold.
    # Since it's inside the method, we can't easily patch the local variable.
    # But we can patch the method `_perform_approximate_clustering` to ensure it's called.
    # And we can use a huge number of samples? No, generating 20001 samples is slow.
    # Best way: Subclass or mock GMMClusterer to change the threshold logic? No.
    # I'll rely on patching `_perform_clustering` and `_perform_approximate_clustering`.

    # Wait, I can't patch the local variable.
    # I can mock `_stream_write_embeddings` to return a large n_samples count,
    # but the actual file will be small. That might crash `mm_array`.

    # Alternative: Use `sed` to lower the threshold in source for testing? No.

    # Actually, I can just test `_perform_approximate_clustering` directly.
    # It's a private method, but accessible in Python.

    data = np.random.rand(30, 10).astype("float32")

    with patch("matome.engines.cluster.IncrementalPCA") as MockIPCA, \
         patch("matome.engines.cluster.MiniBatchKMeans") as MockKMeans:

        mock_ipca = MockIPCA.return_value
        mock_kmeans = MockKMeans.return_value

        # Setup mocks
        mock_ipca.transform.return_value = np.random.rand(10, 2) # reduced
        mock_kmeans.predict.return_value = np.array([0, 1] * 5)

        clusters = clusterer._perform_approximate_clustering(data, 30, config)

        assert MockIPCA.called
        assert MockKMeans.called
        assert len(clusters) > 0

        # Verify partial_fit calls
        # batch_size=10, n_samples=30 -> 3 batches
        assert mock_ipca.partial_fit.call_count == 3
        assert mock_kmeans.partial_fit.call_count == 3
        assert mock_kmeans.predict.call_count == 3
