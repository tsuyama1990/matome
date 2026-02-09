import contextlib
import logging
import uuid
from collections.abc import Iterable, Iterator

from domain_models.config import ProcessingConfig
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

        # Use provided store or create a temporary one
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

            # Recursive Levels
            all_summaries = self._process_levels(clusters, current_level_ids, active_store)

            return self._finalize_tree(current_level_ids, active_store, all_summaries, l0_ids)

    def _process_level_zero(
        self, initial_chunks: Iterable[Chunk], store: DiskChunkStore
    ) -> tuple[list[Cluster], list[NodeID]]:
        """
        Handle Level 0: Embedding, Storage, and Clustering.
        Strictly streaming: embeds, stores, and yields embeddings for clustering.
        """
        current_level_ids: list[NodeID] = []
        stats = {"node_count": 0}

        def l0_embedding_generator() -> Iterator[list[float]]:
            # Streaming chain: initial_chunks -> embedder -> store -> yield
            chunk_stream = self.embedder.embed_chunks(initial_chunks)

            # Process in small batches defined by config
            for chunk_batch_tuple in batched(chunk_stream, self.config.chunk_buffer_size):
                chunk_batch = list(chunk_batch_tuple)

                # Store
                store.add_chunks(chunk_batch)

                # Yield embeddings
                for chunk in chunk_batch:
                    if chunk.embedding is None:
                        msg = f"Chunk {chunk.index} missing embedding."
                        raise ValueError(msg)

                    stats["node_count"] += 1
                    current_level_ids.append(chunk.index)
                    yield chunk.embedding

                if stats["node_count"] % 100 == 0:
                    logger.info(f"Processed {stats['node_count']} chunks (Level 0)...")

        clusters = self.clusterer.cluster_nodes(l0_embedding_generator(), self.config)
        return clusters, current_level_ids

    def _process_levels(
        self,
        initial_clusters: list[Cluster],
        initial_level_ids: list[NodeID],
        store: DiskChunkStore,
    ) -> dict[str, SummaryNode]:
        """
        Recursively process levels (Summarize -> Embed -> Cluster) until root.
        """
        clusters = initial_clusters
        # We need a mutable reference to current level IDs to update them across levels
        # But wait, python passes lists by reference. But we reassign the variable.
        # So we should maintain state locally.
        # Wait, the method signature implies we update state?
        # Actually `initial_level_ids` is L0. We need to track current level.
        # This function should probably return the `all_summaries` map AND update `current_level_ids`?
        # Or better: `current_level_ids` is modified in place? No, we reassign it in loop.
        # This method needs to handle the loop and update the list passed in?
        # Or return the final level IDs?
        # The caller `run` expects `current_level_ids` to point to the ROOT node(s) at end.
        # Since we can't rebind the caller's variable, we should pass it as a container or return it.
        # Let's refactor: this method handles the loop and returns (all_summaries).
        # BUT we need to update `current_level_ids` in the calling scope for `_finalize_tree`.
        # Python list is mutable. If we `clear()` and `extend()`, we modify it in place.

        current_level_ids = initial_level_ids # Alias
        all_summaries: dict[str, SummaryNode] = {}
        level = 0

        while True:
            node_count = len(current_level_ids)
            logger.info(f"Processing Level {level}. Node count: {node_count}")

            if node_count <= 1:
                break

            # Force reduction logic
            if len(clusters) == node_count and node_count > 1:
                logger.warning(
                    f"Clustering failed to reduce nodes (Count: {node_count}). Forcing reduction."
                )
                if node_count < 20:
                    clusters = [Cluster(id=0, level=level, node_indices=list(range(node_count)))]
                else:
                    logger.error("Could not reduce nodes. Stopping recursion.")
                    break

            logger.info(f"Level {level}: Generated {len(clusters)} clusters.")

            level += 1
            new_nodes_iter = self._summarize_clusters(
                clusters, current_level_ids, store, level
            )

            # Collect new IDs for next level
            next_level_ids: list[NodeID] = []

            # Streaming summary storage
            summary_buffer: list[SummaryNode] = []
            BATCH_SIZE = self.config.chunk_buffer_size

            for node in new_nodes_iter:
                all_summaries[node.id] = node
                next_level_ids.append(node.id)
                summary_buffer.append(node)

                if len(summary_buffer) >= BATCH_SIZE:
                    store.add_summaries(summary_buffer)
                    summary_buffer.clear()

            if summary_buffer:
                store.add_summaries(summary_buffer)

            # Update state for next iteration
            current_level_ids.clear()
            current_level_ids.extend(next_level_ids)

            if len(current_level_ids) > 1:
                clusters = self._embed_and_cluster_next_level(current_level_ids, store)
            else:
                clusters = []

        return all_summaries

    def _embed_and_cluster_next_level(
        self, current_level_ids: list[NodeID], store: DiskChunkStore
    ) -> list[Cluster]:
        """
        Embed and cluster nodes for the next level.
        Uses batched retrieval and processing to minimize I/O and memory usage.
        """

        def lx_embedding_generator() -> Iterator[list[float]]:
            # Generator yielding (NodeID, text)
            def node_text_generator() -> Iterator[tuple[NodeID, str]]:
                for nid in current_level_ids:
                    node = store.get_node(nid)
                    if node:
                        yield nid, node.text
                    else:
                        logger.warning(f"Node {nid} not found in store.")

            # Process in batches
            for batch in batched(node_text_generator(), self.config.embedding_batch_size):
                # batch is tuple of (id, text)
                unzipped = list(zip(*batch, strict=True))
                if not unzipped:
                    continue

                ids_tuple = unzipped[0]
                texts_tuple = unzipped[1]

                try:
                    embeddings = self.embedder.embed_strings(texts_tuple)
                    for nid, embedding in zip(ids_tuple, embeddings, strict=True):
                        store.update_node_embedding(nid, embedding)
                        yield embedding
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
        all_summaries: dict[str, SummaryNode],
        l0_ids: list[NodeID],
    ) -> DocumentTree:
        """
        Construct the final DocumentTree.
        """
        if not current_level_ids:
            # If current_level_ids empty but l0_ids not empty (unlikely unless summarization failed completely)
            if l0_ids:
                 msg = "No nodes remaining but chunks exist."
                 raise ValueError(msg)
            # Both empty
            # Create a dummy empty tree? Or raise?
            # Raise for now as it implies empty input/processing
            msg = "No nodes remaining."
            raise ValueError(msg)

        root_id = current_level_ids[0]
        root_node_obj = store.get_node(root_id)

        if not root_node_obj:
            msg = "Root node not found in store."
            raise ValueError(msg)

        if root_node_obj.embedding is None:
            logger.info(f"Generating embedding for root node {root_id}")
            embeddings = list(self.embedder.embed_strings([root_node_obj.text]))
            if embeddings:
                root_node_obj.embedding = embeddings[0]
                store.update_node_embedding(root_id, embeddings[0])
                if isinstance(root_node_obj, SummaryNode):
                    all_summaries[str(root_id)] = root_node_obj

        if isinstance(root_node_obj, Chunk):
            root_node = SummaryNode(
                id=str(uuid.uuid4()),
                text=root_node_obj.text,
                level=1,
                children_indices=[root_node_obj.index],
                metadata={"type": "single_chunk_root"},
            )
            all_summaries[root_node.id] = root_node
        else:
            root_node = root_node_obj

        return DocumentTree(
            root_node=root_node,
            all_nodes=all_summaries,
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
            children_indices: list[NodeID] = []
            cluster_texts: list[str] = []

            for idx_raw in cluster.node_indices:
                idx = int(idx_raw)
                if idx < 0 or idx >= len(current_level_ids):
                    logger.warning(f"Cluster index {idx} out of bounds.")
                    continue

                node_id = current_level_ids[idx]
                node = store.get_node(node_id)
                if not node:
                    continue

                children_indices.append(node_id)
                cluster_texts.append(node.text)

            if not cluster_texts:
                logger.warning(f"Cluster {cluster.id} has no valid nodes to summarize.")
                continue

            combined_text = "\n\n".join(cluster_texts)
            summary_text = self.summarizer.summarize(combined_text, self.config)

            node_id_str = str(uuid.uuid4())
            summary_node = SummaryNode(
                id=node_id_str,
                text=summary_text,
                level=level,
                children_indices=children_indices,
                metadata={"cluster_id": cluster.id},
            )

            yield summary_node
