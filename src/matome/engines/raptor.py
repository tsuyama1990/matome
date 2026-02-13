import contextlib
import logging
import uuid
from collections.abc import Iterable, Iterator

from domain_models.config import ProcessingConfig
from domain_models.data_schema import DIKWLevel, NodeMetadata
from domain_models.manifest import Chunk, Cluster, DocumentTree, SummaryNode
from domain_models.types import NodeID
from matome.engines.embedder import EmbeddingService
from matome.interfaces import Chunker, Clusterer, Summarizer
from matome.utils.compat import batched
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


class RaptorEngine:
    """
    Recursive Abstractive Processing for Tree-Organized Retrieval (RAPTOR) Engine.
    Orchestrates the process of chunking, embedding, clustering, and summarizing text
    to build a hierarchical tree.
    """

    def __init__(
        self,
        chunker: Chunker,
        embedder: EmbeddingService,
        clusterer: Clusterer,
        summarizer: Summarizer,
        config: ProcessingConfig,
    ) -> None:
        """Initialize the RAPTOR engine."""
        self.chunker = chunker
        self.embedder = embedder
        self.clusterer = clusterer
        self.summarizer = summarizer
        self.config = config

    def _process_level_zero(
        self, initial_chunks: Iterable[Chunk], store: DiskChunkStore
    ) -> tuple[list[Cluster], list[NodeID]]:
        """
        Handle Level 0: Embedding, Storage, and Clustering.

        Consumes the initial chunks iterator, embeds them, stores them in the database,
        and then clusters the embeddings. All operations are strictly streaming.
        """
        current_level_ids: list[NodeID] = []
        # Use mutable container to track count within generator
        stats = {"node_count": 0}

        def l0_embedding_generator() -> Iterator[list[list[float]]]:
            # Streaming chain:
            # 1. initial_chunks (Iterator)
            # 2. embedder.embed_chunks (Iterator) -> Yields Chunk with embedding

            chunk_stream = self.embedder.embed_chunks(initial_chunks)

            # Using batched to process small groups of chunks. Use config for buffer size.
            for chunk_batch_tuple in batched(chunk_stream, self.config.chunk_buffer_size):
                # Convert tuple to list for store.add_chunks (interface expects Iterable)
                chunk_batch = list(chunk_batch_tuple)

                # 1. Store batch
                store.add_chunks(chunk_batch)

                # 2. Yield batch of embeddings and collect IDs
                embeddings_batch = []
                for chunk in chunk_batch:
                    if chunk.embedding is None:
                        msg = f"Chunk {chunk.index} missing embedding."
                        raise ValueError(msg)

                    stats["node_count"] += 1
                    current_level_ids.append(chunk.index)
                    embeddings_batch.append(chunk.embedding)

                if stats["node_count"] % 100 == 0:
                    logger.info(f"Processed {stats['node_count']} chunks (Level 0)...")

                yield embeddings_batch

        # cluster_nodes consumes the generator.
        # NOTE: GMMClusterer now handles batches of embeddings
        clusters = self.clusterer.cluster_nodes(l0_embedding_generator(), self.config)

        return clusters, current_level_ids

    def run(self, text: str, store: DiskChunkStore | None = None) -> DocumentTree:
        """
        Execute the RAPTOR pipeline.

        Args:
            text: Input text to process.
            store: Optional persistent store. If None, a temporary store is used (and closed on exit).

        Raises:
            ValueError: If input text is empty or invalid.
        """
        if not text or not isinstance(text, str):
            msg = "Input text must be a non-empty string."
            raise ValueError(msg)

        # Length validation
        if len(text) > self.config.max_input_length:
            msg = f"Input text length ({len(text)}) exceeds maximum allowed ({self.config.max_input_length})."
            raise ValueError(msg)

        logger.info("Starting RAPTOR process: Chunking text.")
        initial_chunks_iter = self.chunker.split_text(text, self.config)

        # Scalability: Removed memory accumulation.
        # Tree reconstruction now relies on recursive building or minimal metadata.

        # Use provided store or create a temporary one
        # If provided, we wrap it in a nullcontext so it doesn't close on exit
        store_ctx: contextlib.AbstractContextManager[DiskChunkStore] = (
            DiskChunkStore() if store is None else contextlib.nullcontext(store)
        )

        with store_ctx as active_store:
            # Level 0
            clusters, current_level_ids = self._process_level_zero(
                initial_chunks_iter, active_store
            )
            # Capture L0 IDs for later reconstruction
            l0_ids = list(current_level_ids)

            current_level_ids = self._process_recursion(clusters, current_level_ids, active_store)

            return self._finalize_tree(current_level_ids, active_store, l0_ids)

    def _process_recursion(
        self,
        clusters: list[Cluster],
        current_level_ids: list[NodeID],
        store: DiskChunkStore,
        start_level: int = 0,
    ) -> list[NodeID]:
        """
        Execute the recursive summarization loop.

        Iteratively clusters and summarizes nodes until a single root node is reached
        or no further reduction is possible.
        """
        level = start_level
        while True:
            node_count = len(current_level_ids)
            logger.info(f"Processing Level {level}. Node count: {node_count}")

            if node_count <= 1:
                break

            # Check for convergence or failure to reduce
            clusters = self._check_reduction_and_force_if_needed(clusters, node_count, level)
            if not clusters:
                break

            logger.info(f"Level {level}: Generated {len(clusters)} clusters.")

            # Summarization Step (Level N -> Level N+1)
            level += 1
            current_level_ids = self._process_summarization_step(
                clusters, current_level_ids, store, level
            )

            # Prepare for next iteration
            if len(current_level_ids) > 1:
                clusters = self._embed_and_cluster_next_level(current_level_ids, store)
            else:
                clusters = []

        return current_level_ids

    def _check_reduction_and_force_if_needed(
        self, clusters: list[Cluster], node_count: int, level: int
    ) -> list[Cluster]:
        """
        Ensure that clustering is actually reducing the node count.
        If not, force reduction for small sets or stop recursion.
        """
        if len(clusters) == node_count and node_count > 1:
            logger.warning(
                f"Clustering failed to reduce nodes (Count: {node_count}). Forcing reduction."
            )
            # If small enough, just collapse everything into one root
            if node_count < 20:
                return [Cluster(id=0, level=level, node_indices=list(range(node_count)))]

            logger.error("Could not reduce nodes. Stopping recursion.")
            return []
        return clusters

    def _process_summarization_step(
        self,
        clusters: list[Cluster],
        previous_level_ids: list[NodeID],
        store: DiskChunkStore,
        level: int,
    ) -> list[NodeID]:
        """
        Perform the summarization for a single level and persist results.
        Returns the list of new summary node IDs.
        """
        new_nodes_iter = self._summarize_clusters(clusters, previous_level_ids, store, level)
        new_level_ids: list[NodeID] = []

        # Process summary nodes in batches
        summary_buffer: list[SummaryNode] = []
        BATCH_SIZE = self.config.chunk_buffer_size

        for node in new_nodes_iter:
            new_level_ids.append(node.id)
            summary_buffer.append(node)

            if len(summary_buffer) >= BATCH_SIZE:
                store.add_summaries(summary_buffer)
                summary_buffer.clear()

        if summary_buffer:
            store.add_summaries(summary_buffer)

        return new_level_ids

    def _yield_node_texts(
        self, node_ids: list[NodeID], store: DiskChunkStore
    ) -> Iterator[tuple[NodeID, str]]:
        """Yield (id, text) tuples from store efficiently."""
        for batch_ids in batched(node_ids, self.config.chunk_buffer_size):
            batch_ids_list = list(batch_ids)
            nodes_map = store.get_nodes(batch_ids_list)

            for nid in batch_ids_list:
                node = nodes_map.get(nid)
                if not node:
                    # Fallback check
                    alt_key: int | str | None = None
                    if isinstance(nid, int):
                        alt_key = str(nid)
                    elif isinstance(nid, str) and nid.isdigit():
                        alt_key = int(nid)

                    if alt_key is not None and alt_key in nodes_map:
                        node = nodes_map[alt_key]

                if node:
                    yield nid, node.text
                else:
                    logger.warning(f"Node {nid} not found in store.")

    def _embed_and_cluster_next_level(
        self, current_level_ids: list[NodeID], store: DiskChunkStore
    ) -> list[Cluster]:
        """
        Perform embedding and clustering for the next level (summaries).
        """

        def lx_embedding_generator() -> Iterator[list[list[float]]]:
            # Strategy: Batched processing manually
            # Using config.embedding_batch_size to bound memory usage per batch.
            node_iter = self._yield_node_texts(current_level_ids, store)

            for batch in batched(node_iter, self.config.embedding_batch_size):
                unzipped = list(zip(*batch, strict=True))
                if not unzipped:
                    continue

                ids_tuple = unzipped[0]
                texts_tuple = unzipped[1]

                # Embed batch (returns iterator)
                try:
                    # Fix: Ensure embed_strings is treated as iterator source
                    # If implementation returns list, iter() handles it.
                    embeddings_iter = self.embedder.embed_strings(texts_tuple)
                    embeddings_batch = []
                    updates: list[tuple[NodeID, list[float]]] = []

                    for nid, embedding in zip(ids_tuple, embeddings_iter, strict=True):
                        updates.append((nid, embedding))
                        embeddings_batch.append(embedding)

                    # Bulk update
                    store.update_embeddings(updates)

                    yield embeddings_batch

                except Exception as e:
                    logger.exception("Failed to embed batch during next level clustering.")
                    msg = "Embedding failed during recursion."
                    raise RuntimeError(msg) from e

        try:
            return self.clusterer.cluster_nodes(lx_embedding_generator(), self.config)
        except Exception as e:
            logger.exception("Clustering failed during recursion.")
            msg = "Clustering failed during recursion."
            raise RuntimeError(msg) from e

    def _finalize_tree(
        self,
        current_level_ids: list[NodeID],
        store: DiskChunkStore,
        l0_ids: list[NodeID],
    ) -> DocumentTree:
        """
        Construct the final DocumentTree.
        """
        if not current_level_ids:
            if not l0_ids:
                pass
            msg = "No nodes remaining."
            raise ValueError(msg)

        root_id = current_level_ids[0]
        root_node_obj = store.get_node(root_id)

        if not root_node_obj:
            msg = "Root node not found in store."
            raise ValueError(msg)

        # Ensure root node has embedding
        if root_node_obj.embedding is None:
            logger.info(f"Generating embedding for root node {root_id}")
            # Generate single embedding - wrap in list/iter
            embeddings = list(self.embedder.embed_strings([root_node_obj.text]))
            if embeddings:
                root_node_obj.embedding = embeddings[0]
                store.update_node_embedding(root_id, embeddings[0])

        if isinstance(root_node_obj, Chunk):
            # Create a virtual summary root for single chunk
            root_node = SummaryNode(
                id=str(uuid.uuid4()),
                text=root_node_obj.text,
                level=1,
                children_indices=[root_node_obj.index],
                metadata=NodeMetadata(dikw_level=DIKWLevel.DATA, type="single_chunk_root"),
            )
            # We must persist this virtual root if we want exporters to find it?
            # Or just return it in memory.
            # Exporters traverse via IDs. If they call store.get_node(virtual_root.id), it fails.
            # So we MUST save it.
            store.add_summaries([root_node])
        else:
            root_node = root_node_obj

        return DocumentTree(
            root_node=root_node,
            leaf_chunk_ids=l0_ids,
            metadata={"levels": root_node.level},
        )

    def _summarize_clusters(
        self,
        clusters: list[Cluster],
        current_level_ids: list[NodeID],
        store: DiskChunkStore,
        level: int,
    ) -> Iterator[SummaryNode]:
        """
        Process clusters to generate summaries (streaming).
        """
        for cluster in clusters:
            children_indices, cluster_texts = self._gather_cluster_data(
                cluster, current_level_ids, store
            )

            if not cluster_texts:
                logger.warning(f"Cluster {cluster.id} has no valid nodes to summarize.")
                continue

            node_id_str = str(uuid.uuid4())

            # Default to INFORMATION for generic summaries
            context = {
                "id": node_id_str,
                "level": level,
                "children_indices": children_indices,
                "metadata": {"cluster_id": cluster.id},
            }

            summary_node = self.summarizer.summarize(cluster_texts, context=context)

            yield summary_node

    def _gather_cluster_data(
        self,
        cluster: Cluster,
        current_level_ids: list[NodeID],
        store: DiskChunkStore,
    ) -> tuple[list[NodeID], list[str]]:
        """Retrieve node IDs and texts for a cluster."""
        children_indices: list[NodeID] = []
        cluster_texts: list[str] = []

        # Gather valid node IDs first
        valid_node_ids: list[NodeID] = []
        for idx_raw in cluster.node_indices:
            idx = int(idx_raw)
            if idx < 0 or idx >= len(current_level_ids):
                logger.warning(f"Cluster index {idx} out of bounds for current level nodes.")
                continue
            valid_node_ids.append(current_level_ids[idx])

        if not valid_node_ids:
            logger.warning(f"Cluster {cluster.id} has no valid node indices.")
            return [], []

        # Batch retrieve nodes
        nodes_map = store.get_nodes(valid_node_ids)

        for node_id in valid_node_ids:
            node = nodes_map.get(node_id)
            # Fallback check for int/str key mismatch
            if not node and isinstance(node_id, (int, str)):
                alt_key: int | str | None = None
                if isinstance(node_id, int):
                    alt_key = str(node_id)
                elif isinstance(node_id, str) and node_id.isdigit():
                    alt_key = int(node_id)

                if alt_key is not None and alt_key in nodes_map:
                    node = nodes_map[alt_key]

            if not node:
                continue

            children_indices.append(node_id)
            cluster_texts.append(node.text)

        return children_indices, cluster_texts
