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

    def _process_level_zero(
        self, initial_chunks: Iterable[Chunk], store: DiskChunkStore
    ) -> tuple[list[Cluster], list[NodeID]]:
        """
        Handle Level 0: Embedding, Storage, and Clustering.

        Consumes the initial chunks iterator, embeds them, stores them in the database
        (batched), and then clusters the embeddings. All operations are strictly streaming.
        """
        current_level_ids: list[NodeID] = []
        # Use mutable container to track count within generator
        stats = {"node_count": 0}

        def l0_embedding_generator() -> Iterator[list[float]]:
            chunk_buffer: list[Chunk] = []

            # Embed chunks (streaming from initial_chunks iterator)
            for chunk in self.embedder.embed_chunks(initial_chunks):
                if chunk.embedding is None:
                    msg = f"Chunk {chunk.index} missing embedding."
                    raise ValueError(msg)

                stats["node_count"] += 1
                if stats["node_count"] % 100 == 0:
                    logger.info(f"Processed {stats['node_count']} chunks (Level 0)...")

                yield chunk.embedding

                # Buffer chunks for storage to avoid N+1 DB transactions
                chunk_buffer.append(chunk)
                current_level_ids.append(chunk.index)

                if len(chunk_buffer) >= self.config.chunk_buffer_size:
                    store.add_chunks(chunk_buffer)
                    chunk_buffer.clear()

            # Flush remaining chunks
            if chunk_buffer:
                store.add_chunks(chunk_buffer)

        # cluster_nodes consumes the generator.
        # This will drive the loop above, which drives storage and counting.
        clusters = self.clusterer.cluster_nodes(l0_embedding_generator(), self.config)

        return clusters, current_level_ids

    def run(self, text: str, store: DiskChunkStore | None = None) -> DocumentTree:
        """
        Execute the RAPTOR pipeline.

        Args:
            text: Input text to process.
            store: Optional persistent store. If None, a temporary store is used (and closed on exit).
        """
        logger.info("Starting RAPTOR process: Chunking text.")
        initial_chunks_iter = self.chunker.split_text(text, self.config)

        all_summaries: dict[str, SummaryNode] = {}

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

            level = 0
            while True:
                node_count = len(current_level_ids)
                logger.info(f"Processing Level {level}. Node count: {node_count}")

                if node_count <= 1:
                    break

                # Force reduction if clustering returns same number of clusters as nodes
                if len(clusters) == node_count and node_count > 1:
                    logger.warning(
                        f"Clustering failed to reduce nodes (Count: {node_count}). Forcing reduction."
                    )
                    # Fallback: Merge all into one cluster if node_count is small, else break?
                    # If we break, we stop summarization.
                    # Let's collapse to 1 cluster if small enough.
                    if node_count < 20:
                        clusters = [Cluster(id=0, level=level, node_indices=list(range(node_count)))]
                    else:
                        # Just proceed, maybe next level will cluster better?
                        # No, if we don't reduce, we loop forever or just summarize 1-to-1?
                        # Summarize 1-to-1 is useless.
                        # We MUST reduce.
                        # Let's break for safety to avoid infinite loops if we can't reduce.
                        logger.error("Could not reduce nodes. Stopping recursion.")
                        break

                logger.info(f"Level {level}: Generated {len(clusters)} clusters.")

                # Summarization
                level += 1
                new_nodes_iter = self._summarize_clusters(
                    clusters, current_level_ids, active_store, level
                )

                current_level_ids = []

                # Process summary nodes in batches
                summary_buffer: list[SummaryNode] = []
                BATCH_SIZE = self.config.chunk_buffer_size

                for node in new_nodes_iter:
                    all_summaries[node.id] = node
                    current_level_ids.append(node.id)
                    summary_buffer.append(node)

                    if len(summary_buffer) >= BATCH_SIZE:
                        active_store.add_summaries(summary_buffer)
                        summary_buffer.clear()

                if summary_buffer:
                    active_store.add_summaries(summary_buffer)

                if len(current_level_ids) > 1:
                    # Embed and Cluster for next level
                    clusters = self._embed_and_cluster_next_level(current_level_ids, active_store)
                else:
                    clusters = []

            return self._finalize_tree(current_level_ids, active_store, all_summaries, l0_ids)

    def _embed_and_cluster_next_level(
        self, current_level_ids: list[NodeID], store: DiskChunkStore
    ) -> list[Cluster]:
        """
        Perform embedding and clustering for the next level (summaries).

        Retrieves text for the current level nodes from the store, generates embeddings,
        updates the store with new embeddings, and clusters them.
        """

        def lx_embedding_generator() -> Iterator[list[float]]:
            # Generator that yields (id, text) tuples
            def node_text_generator() -> Iterator[tuple[NodeID, str]]:
                for nid in current_level_ids:
                    node = store.get_node(nid)
                    if node:
                        yield nid, node.text
                    else:
                        logger.warning(
                            f"Node {nid} not found in store during next level clustering."
                        )

            # Strategy: Batched processing manually
            # We process in batches to avoid loading all texts
            for batch in batched(node_text_generator(), self.config.embedding_batch_size):
                # batch is a tuple of (nid, text)
                ids = [item[0] for item in batch]
                texts = [item[1] for item in batch]

                # Embed batch (returns iterator)
                embeddings = self.embedder.embed_strings(texts)

                for nid, embedding in zip(ids, embeddings, strict=True):
                    store.update_node_embedding(nid, embedding)
                    yield embedding

        return self.clusterer.cluster_nodes(lx_embedding_generator(), self.config)

    def _finalize_tree(
        self,
        current_level_ids: list[NodeID],
        store: DiskChunkStore,
        all_summaries: dict[str, SummaryNode],
        l0_ids: list[NodeID],
    ) -> DocumentTree:
        """
        Construct the final DocumentTree.

        Builds the tree structure from the final root node down to the leaf chunks.
        """
        if not current_level_ids:
            # If input was empty?
            if not l0_ids:
                # Should return empty tree if no chunks at all
                # But we need a dummy root? Or empty tree?
                # Returning minimal dummy tree for safety if logic requires return
                pass
            # If current_level_ids empty but l0_ids not empty (unlikely unless summarization failed completely)
            msg = "No nodes remaining."
            raise ValueError(msg)

        root_id = current_level_ids[0]
        root_node_obj = store.get_node(root_id)

        if not root_node_obj:
            msg = "Root node not found in store."
            raise ValueError(msg)

        # Ensure root node has embedding (it might be skipped in loop if it was the only node)
        if root_node_obj.embedding is None:
            logger.info(f"Generating embedding for root node {root_id}")
            # Generate single embedding
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

        Iterates over clusters, retrieves member texts, and invokes the summarizer.
        Yields SummaryNodes for the next level.
        """
        for cluster in clusters:
            children_indices: list[NodeID] = []
            cluster_texts: list[str] = []

            for idx_raw in cluster.node_indices:
                idx = int(idx_raw)
                # Check bounds
                if idx < 0 or idx >= len(current_level_ids):
                    logger.warning(f"Cluster index {idx} out of bounds for current level nodes.")
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

            # Note: For very large clusters, joining texts might still be memory intensive.
            # But the summarizer typically takes a string.
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
