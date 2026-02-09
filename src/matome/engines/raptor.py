import contextlib
import logging
import uuid
from collections.abc import Iterable, Iterator

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree, SummaryNode
from domain_models.types import NodeID
from matome.engines.embedder import EmbeddingService
from matome.interfaces import Chunker, Clusterer, Summarizer
from matome.utils.store import DiskChunkStore
from matome.utils.compat import batched

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
        """
        logger.info("Starting RAPTOR process: Chunking text.")
        initial_chunks_iter = self.chunker.split_text(text, self.config)

        all_summaries: dict[str, SummaryNode] = {}

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

            level = 0
            while True:
                node_count = len(current_level_ids)
                logger.info(f"Processing Level {level}. Node count: {node_count}")

                if node_count <= 1:
                    break

                if len(clusters) == node_count:
                    # If clustering returned 1 cluster per node (or just one big cluster of all),
                    # we might be done or need one last summary.
                    pass

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
                    clusters = self._next_level_clustering(current_level_ids, active_store)
                else:
                    clusters = []

            return self._finalize_tree(current_level_ids, active_store, all_summaries, l0_ids)

    def _process_level_zero(
        self, initial_chunks: Iterable[Chunk], store: DiskChunkStore
    ) -> tuple[list[Cluster], list[NodeID]]:
        """
        Handle Level 0: Embedding, Storage, and Clustering.
        """
        current_level_ids: list[NodeID] = []

        # Create a generator that yields embeddings AND populates current_level_ids/store
        embedding_stream = self._embed_and_store_l0(initial_chunks, store, current_level_ids)

        # cluster_nodes consumes the generator
        clusters = self.clusterer.cluster_nodes(embedding_stream, self.config)

        return clusters, current_level_ids

    def _embed_and_store_l0(
        self,
        initial_chunks: Iterable[Chunk],
        store: DiskChunkStore,
        id_tracker: list[NodeID]
    ) -> Iterator[list[float]]:
        """
        Generator that embeds chunks, stores them, tracks their IDs, and yields embeddings.
        """
        chunk_buffer: list[Chunk] = []
        node_count = 0

        # Embed chunks (streaming from initial_chunks iterator)
        for chunk in self.embedder.embed_chunks(initial_chunks):
            if chunk.embedding is None:
                msg = f"Chunk {chunk.index} missing embedding."
                raise ValueError(msg)

            node_count += 1
            if node_count % 100 == 0:
                logger.info(f"Processed {node_count} chunks (Level 0)...")

            yield chunk.embedding

            # Buffer chunks for storage to avoid N+1 DB transactions
            chunk_buffer.append(chunk)
            id_tracker.append(chunk.index)

            if len(chunk_buffer) >= self.config.chunk_buffer_size:
                store.add_chunks(chunk_buffer)
                chunk_buffer.clear()

        # Flush remaining chunks
        if chunk_buffer:
            store.add_chunks(chunk_buffer)

    def _next_level_clustering(
        self, current_level_ids: list[NodeID], store: DiskChunkStore
    ) -> list[Cluster]:
        """
        Perform embedding and clustering for the next level (summaries).
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

            # Process in batches
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
                # Validation: ensure idx is within range
                if idx < 0 or idx >= len(current_level_ids):
                    logger.warning(f"Cluster node index {idx} out of range.")
                    continue

                node_id = current_level_ids[idx]
                node = store.get_node(node_id)
                if not node:
                    continue

                children_indices.append(node_id)
                cluster_texts.append(node.text)

            if not cluster_texts:
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
            # If input was empty?
            if not l0_ids:
                # Returning minimal dummy tree for safety
                dummy_root = SummaryNode(
                    id=str(uuid.uuid4()),
                    text="",
                    level=1,
                    children_indices=[],
                    metadata={"type": "empty_root"},
                )
                return DocumentTree(
                    root_node=dummy_root,
                    all_nodes={},
                    leaf_chunk_ids=[],
                    metadata={"status": "empty"},
                )

            msg = "No nodes remaining but L0 chunks exist. Summarization error?"
            raise ValueError(msg)

        root_id = current_level_ids[0]
        root_node_obj = store.get_node(root_id)

        if not root_node_obj:
            msg = "Root node not found in store."
            raise ValueError(msg)

        # Ensure root node has embedding
        if root_node_obj.embedding is None:
            logger.info(f"Generating embedding for root node {root_id}")
            embeddings = list(self.embedder.embed_strings([root_node_obj.text]))
            if embeddings:
                root_node_obj.embedding = embeddings[0]
                store.update_node_embedding(root_id, embeddings[0])
                if isinstance(root_node_obj, SummaryNode):
                    all_summaries[str(root_id)] = root_node_obj

        if isinstance(root_node_obj, Chunk):
            # Promote single chunk to SummaryNode root
            root_node = SummaryNode(
                id=str(uuid.uuid4()),
                text=root_node_obj.text,
                level=1,
                children_indices=[root_node_obj.index],
                embedding=root_node_obj.embedding,
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
