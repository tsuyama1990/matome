import contextlib
import logging
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import IncrementalPCA

from domain_models.config import ClusteringAlgorithm, ProcessingConfig
from domain_models.constants import MIN_CLUSTERING_SAMPLES
from domain_models.manifest import Cluster
from domain_models.types import NodeID

logger = logging.getLogger(__name__)


class GMMClusterer:
    """
    Engine for clustering text chunks/nodes.
    Implements the Clusterer protocol.

    Uses IncrementalPCA and MiniBatchKMeans to provide true streaming clustering,
    ensuring memory safety even for very large datasets.
    """

    def cluster_nodes(
        self, embeddings: Iterable[tuple[NodeID, list[float]]], config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Clusters the nodes based on their embeddings.

        Args:
            embeddings: An iterable of (NodeID, vector) tuples.
            config: Processing configuration.

        Returns:
            A list of Cluster objects containing indices of grouped nodes.
        """
        self._validate_algorithm(config)

        # Batch size for disk writing (from config)
        write_batch_size = config.write_batch_size

        # Create temp files for memory mapping and ID storage
        fd_emb, tf_emb = tempfile.mkstemp()
        os.close(fd_emb)
        path_emb = Path(tf_emb)

        fd_ids, tf_ids = tempfile.mkstemp()
        os.close(fd_ids)
        path_ids = Path(tf_ids)

        try:
            # Stream write embeddings and IDs to disk.
            n_samples, dim = self._stream_write_data(embeddings, path_emb, path_ids, write_batch_size)

            if n_samples == 0:
                return []

            # Handle edge cases (small datasets)
            edge_case_result = self._handle_edge_cases(n_samples, path_ids)
            if edge_case_result:
                return edge_case_result

            # Open as memmap
            mm_array = np.memmap(tf_emb, dtype="float32", mode="r", shape=(n_samples, dim))

            try:
                return self._perform_clustering(mm_array, n_samples, path_ids, config)
            finally:
                del mm_array

        finally:
            with contextlib.suppress(OSError):
                if path_emb.exists():
                    path_emb.unlink()
                if path_ids.exists():
                    path_ids.unlink()

    def _stream_write_data(
        self,
        embeddings: Iterable[tuple[NodeID, list[float]]],
        path_emb: Path,
        path_ids: Path,
        batch_size: int
    ) -> tuple[int, int]:
        """
        Stream embeddings and IDs to disk in batches.
        """
        n_samples = 0
        dim = 0
        emb_buffer: list[list[float]] = []
        id_buffer: list[str] = []

        with path_emb.open("wb") as f_emb, path_ids.open("w", encoding="utf-8") as f_ids:
            for i, (nid, vec) in enumerate(embeddings):
                if n_samples == 0 and len(emb_buffer) == 0:
                    dim = len(vec)
                    if dim == 0:
                        msg = "Embedding dimension cannot be zero."
                        raise ValueError(msg)

                if len(vec) != dim:
                    msg = f"Embedding dimension mismatch at index {i}."
                    raise ValueError(msg)

                emb_buffer.append(vec)
                id_buffer.append(str(nid))

                if len(emb_buffer) >= batch_size:
                    self._flush_buffers(f_emb, f_ids, emb_buffer, id_buffer)
                    n_samples += len(emb_buffer)
                    emb_buffer.clear()
                    id_buffer.clear()

            # Final flush
            if emb_buffer:
                self._flush_buffers(f_emb, f_ids, emb_buffer, id_buffer)
                n_samples += len(emb_buffer)
                emb_buffer.clear()
                id_buffer.clear()

        return n_samples, dim

    def _flush_buffers(self, f_emb: BinaryIO, f_ids: Any, emb_buffer: list[list[float]], id_buffer: list[str]) -> None:
        """Helper to write buffers to disk."""
        # Embeddings
        try:
            np_batch = np.array(emb_buffer, dtype="float32")
        except ValueError as e:
            msg = f"Failed to create array from buffer: {e}"
            raise ValueError(msg) from e

        if not np.isfinite(np_batch).all():
            msg = "Embeddings contain NaN or Infinity values."
            raise ValueError(msg)

        np_batch.tofile(f_emb)

        # IDs (newline delimited)
        f_ids.write("\n".join(id_buffer) + "\n")

    def _validate_algorithm(self, config: ProcessingConfig) -> None:
        """Validate that the configured algorithm is supported."""
        algo = config.clustering_algorithm
        if algo != ClusteringAlgorithm.GMM:
            msg = f"Unsupported clustering algorithm: {algo}. Only '{ClusteringAlgorithm.GMM.value}' is supported."
            raise ValueError(msg)

    def _handle_edge_cases(self, n_samples: int, path_ids: Path) -> list[Cluster] | None:
        """Handle small datasets."""
        if n_samples <= MIN_CLUSTERING_SAMPLES:
            node_ids = self._read_all_ids(path_ids)
            logger.info(
                f"Dataset too small for clustering ({n_samples} samples). Grouping all into one cluster."
            )
            return [Cluster(id=0, level=0, node_indices=node_ids)]
        return None

    def _read_all_ids(self, path_ids: Path) -> list[NodeID]:
        """Read all IDs from file."""
        with path_ids.open("r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def _perform_clustering(
        self, data: np.ndarray, n_samples: int, path_ids: Path, config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Execute streaming clustering using IncrementalPCA and MiniBatchKMeans.
        Avoids loading the entire dataset into memory.
        """
        n_components = config.umap_n_components
        # Use config.n_clusters or heuristic.
        n_clusters = config.n_clusters or min(int(np.sqrt(n_samples)), 50)

        logger.info(
            f"Starting Clustering for {n_samples} nodes. "
            f"PCA components={n_components}, KMeans clusters={n_clusters}."
        )

        try:
            # 1. Incremental PCA Training
            ipca = IncrementalPCA(n_components=n_components)
            batch_size = config.write_batch_size

            # Loop over memmap in batches
            for i in range(0, n_samples, batch_size):
                batch = data[i : i + batch_size]
                ipca.partial_fit(batch)

            # 2. MiniBatchKMeans Training
            # We must transform and feed to KMeans
            kmeans = MiniBatchKMeans(
                n_clusters=n_clusters,
                random_state=config.random_state,
                batch_size=batch_size,
                n_init="auto",
            )

            for i in range(0, n_samples, batch_size):
                batch = data[i : i + batch_size]
                reduced_batch = ipca.transform(batch)
                kmeans.partial_fit(reduced_batch)

            # 3. Predict Labels (Final Pass)
            labels_list = []
            for i in range(0, n_samples, batch_size):
                batch = data[i : i + batch_size]
                reduced_batch = ipca.transform(batch)
                batch_labels = kmeans.predict(reduced_batch)
                labels_list.append(batch_labels)

            labels = np.concatenate(labels_list)
            return self._form_clusters(labels, path_ids)

        except Exception as e:
            logger.exception("Clustering failed.")
            msg = f"Clustering failed: {e}"
            raise RuntimeError(msg) from e

    def _form_clusters(self, labels: np.ndarray, path_ids: Path) -> list[Cluster]:
        """Convert hard clustering labels into Cluster objects via streaming."""
        # cluster_id -> list[NodeID]
        cluster_map: dict[int, list[NodeID]] = {}

        with path_ids.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                nid = line.strip()
                if not nid:
                    continue

                label = int(labels[i])
                if label not in cluster_map:
                    cluster_map[label] = []
                cluster_map[label].append(nid)

        clusters: list[Cluster] = []
        for cluster_id, mapped_ids in cluster_map.items():
            if mapped_ids:
                clusters.append(Cluster(id=cluster_id, level=0, node_indices=mapped_ids))

        return clusters
