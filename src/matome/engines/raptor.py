import contextlib
import logging
import uuid
from collections.abc import Iterable, Iterator

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel, NodeID
from matome.agents.strategies import ActionStrategy, KnowledgeStrategy, WisdomStrategy
from matome.engines.embedder import EmbeddingService
from matome.interfaces import Chunker, Clusterer, PromptStrategy, Summarizer
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

        def l0_embedding_generator() -> Iterator[list[float]]:
            # Streaming chain:
            # 1. initial_chunks (Iterator)
            # 2. embedder.embed_chunks (Iterator) -> Yields Chunk with embedding

            chunk_stream = self.embedder.embed_chunks(initial_chunks)

            # Use batched() to handle chunks in batches efficiently
            for chunk_batch in batched(chunk_stream, self.config.chunk_buffer_size):
                # 1. Store batch
                store.add_chunks(chunk_batch)

                # 2. Yield embeddings and collect IDs
                for c in chunk_batch:
                    if c.embedding is None:
                        msg = f"Chunk {c.index} missing embedding."
                        raise ValueError(msg)
                    stats["node_count"] += 1
                    current_level_ids.append(c.index)
                    yield c.embedding

                if stats["node_count"] % 100 == 0:
                    logger.info(f"Processed {stats['node_count']} chunks (Level 0)...")

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

            current_level_ids = self._process_recursion(
                clusters, current_level_ids, active_store, all_summaries
            )

            return self._finalize_tree(current_level_ids, active_store, all_summaries, l0_ids)

    def _process_recursion(
        self,
        clusters: list[Cluster],
        current_level_ids: list[NodeID],
        store: DiskChunkStore,
        all_summaries: dict[str, SummaryNode],
        start_level: int = 0,
    ) -> list[NodeID]:
        """
        Execute the recursive summarization loop.
        """
        level = start_level
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
                if node_count < 20:
                    clusters = [Cluster(id=0, level=level, node_indices=list(range(node_count)))]
                else:
                    logger.error("Could not reduce nodes. Stopping recursion.")
                    break

            logger.info(f"Level {level}: Generated {len(clusters)} clusters.")

            # Summarization
            level += 1
            new_nodes_iter = self._summarize_clusters(clusters, current_level_ids, store, level)

            current_level_ids = []

            # Process summary nodes in batches
            for summary_batch in batched(new_nodes_iter, self.config.chunk_buffer_size):
                store.add_summaries(summary_batch)
                for node in summary_batch:
                    all_summaries[node.id] = node
                    current_level_ids.append(node.id)

            if len(current_level_ids) > 1:
                # Embed and Cluster for next level
                clusters = self._embed_and_cluster_next_level(current_level_ids, store)
            else:
                clusters = []

        return current_level_ids

    def _embed_and_cluster_next_level(
        self, current_level_ids: list[NodeID], store: DiskChunkStore
    ) -> list[Cluster]:
        """
        Perform embedding and clustering for the next level (summaries).
        """

        def lx_embedding_generator() -> Iterator[list[float]]:
            return self._batched_embedding_generator(current_level_ids, store)

        try:
            return self.clusterer.cluster_nodes(lx_embedding_generator(), self.config)
        except Exception as e:
            logger.exception("Clustering failed during recursion.")
            msg = "Clustering failed during recursion."
            raise RuntimeError(msg) from e

    def _batched_embedding_generator(
        self, current_level_ids: list[NodeID], store: DiskChunkStore
    ) -> Iterator[list[float]]:
        """Yields embeddings in batches, processing from store."""

        def node_text_generator() -> Iterator[tuple[NodeID, str]]:
            for nid in current_level_ids:
                node = store.get_node(nid)
                if node:
                    yield nid, node.text
                else:
                    logger.warning(f"Node {nid} not found in store during next level clustering.")

        # Stream node texts and batch them for embedding
        for batch in batched(node_text_generator(), self.config.embedding_batch_size):
            # batch is tuple of (nid, text)
            ids_batch = [item[0] for item in batch]
            texts_batch = [item[1] for item in batch]

            yield from self._process_embedding_batch(ids_batch, texts_batch, store)

    def _process_embedding_batch(
        self,
        ids_buffer: list[NodeID],
        texts_buffer: list[str],
        store: DiskChunkStore,
    ) -> Iterator[list[float]]:
        """Process a single batch of embeddings."""
        try:
            embeddings_iter = self.embedder.embed_strings(texts_buffer)
            # embed_strings returns an iterator, but we need to zip it with IDs.
            # zip will consume it.
            for nid_out, embedding in zip(ids_buffer, embeddings_iter, strict=True):
                store.update_node_embedding(nid_out, embedding)
                yield embedding
        except Exception as e:
            logger.exception("Failed to embed batch during next level clustering.")
            msg = "Embedding failed during recursion."
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
            if not l0_ids:
                # Should return empty tree if no chunks at all
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
                metadata=NodeMetadata(dikw_level=DIKWLevel.DATA, type="single_chunk_root"),
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
            children_indices, cluster_texts = self._get_cluster_content(
                cluster, current_level_ids, store
            )

            if not cluster_texts:
                logger.warning(f"Cluster {cluster.id} has no valid nodes to summarize.")
                continue

            texts_to_pass = self._truncate_cluster_text(cluster.id, cluster_texts)

            strategy, dikw = self._get_strategy_for_level(level)

            summary_text = self.summarizer.summarize(
                texts_to_pass, self.config, level=level, strategy=strategy
            )

            yield SummaryNode(
                id=str(uuid.uuid4()),
                text=summary_text,
                level=level,
                children_indices=children_indices,
                metadata=NodeMetadata(cluster_id=cluster.id, dikw_level=dikw),
            )

    def _get_cluster_content(
        self,
        cluster: Cluster,
        current_level_ids: list[NodeID],
        store: DiskChunkStore,
    ) -> tuple[list[NodeID], list[str]]:
        """Retrieve content for a single cluster."""
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

        return children_indices, cluster_texts

    def _truncate_cluster_text(self, cluster_id: NodeID, texts: list[str]) -> list[str]:
        """Truncate list of texts if total length exceeds limit."""
        total_chars = sum(len(t) for t in texts)
        if total_chars <= self.config.max_input_length:
            return texts

        logger.warning(
            f"Cluster {cluster_id} text size ({total_chars}) exceeds max input length. Truncating."
        )
        current_len = 0
        truncated_texts = []
        for t in texts:
            if current_len + len(t) > self.config.max_input_length:
                break
            truncated_texts.append(t)
            current_len += len(t)
        return truncated_texts

    def _get_strategy_for_level(self, level: int) -> tuple[PromptStrategy, DIKWLevel]:
        """Determine strategy and DIKW level based on recursion depth."""
        if level == 1:
            return ActionStrategy(), DIKWLevel.INFORMATION
        if level == 2:
            return KnowledgeStrategy(), DIKWLevel.KNOWLEDGE
        return WisdomStrategy(), DIKWLevel.WISDOM
