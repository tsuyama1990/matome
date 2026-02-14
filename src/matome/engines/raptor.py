import contextlib
import logging
import uuid
from collections.abc import Iterable, Iterator

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel, NodeID
from matome.agents.strategies import (
    BaseSummaryStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)
from matome.engines.embedder import EmbeddingService
from matome.exceptions import ClusteringError, MatomeError, SummarizationError
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

        # Strategy lookup map to avoid complex conditionals
        self._strategy_map: dict[str, type[PromptStrategy]] = {
            "wisdom": WisdomStrategy,
            "knowledge": KnowledgeStrategy,
            "information": InformationStrategy,
        }

    def _get_strategy_for_level(self, current_level: int, is_final_layer: bool) -> PromptStrategy:
        """
        Determine the PromptStrategy based on the current level and topology.
        """
        mapping = self.config.strategy_mapping

        if not mapping:
            return BaseSummaryStrategy()

        strategy_name = ""

        if is_final_layer:
             strategy_name = mapping.get(DIKWLevel.WISDOM, "wisdom")
        elif current_level == 0:
             strategy_name = mapping.get(DIKWLevel.INFORMATION, "information")
        else:
             strategy_name = mapping.get(DIKWLevel.KNOWLEDGE, "knowledge")

        strategy_class = self._strategy_map.get(strategy_name)
        if strategy_class:
            return strategy_class()

        return BaseSummaryStrategy()

    def _process_level_zero(
        self, initial_chunks: Iterable[Chunk], store: DiskChunkStore
    ) -> tuple[list[Cluster], list[NodeID]]:
        """
        Handle Level 0: Embedding, Storage, and Clustering.
        Strictly streaming.
        """
        current_level_ids: list[NodeID] = []
        stats = {"node_count": 0}

        def l0_embedding_generator() -> Iterator[list[float]]:
            try:
                chunk_stream = self.embedder.embed_chunks(initial_chunks)

                for chunk_batch_tuple in batched(chunk_stream, self.config.chunk_buffer_size):
                    # Keep as tuple, do NOT convert to list to save memory
                    store.add_chunks(chunk_batch_tuple)

                    for chunk in chunk_batch_tuple:
                        if chunk.embedding is None:
                            msg = f"Chunk {chunk.index} missing embedding."
                            raise ValueError(msg)

                        stats["node_count"] += 1
                        current_level_ids.append(chunk.index)
                        yield chunk.embedding

                    if stats["node_count"] % 100 == 0:
                        logger.info(f"Processed {stats['node_count']} chunks (Level 0)...")
            except Exception as e:
                logger.exception("Level 0 processing failed.")
                msg = "Level 0 processing failed"
                raise MatomeError(msg) from e

        try:
            clusters = self.clusterer.cluster_nodes(l0_embedding_generator(), self.config)
        except Exception as e:
             msg = "Clustering failed at Level 0"
             raise ClusteringError(msg) from e

        return clusters, current_level_ids

    def run(self, text: str, store: DiskChunkStore | None = None) -> DocumentTree:
        """
        Execute the RAPTOR pipeline.
        """
        if not text or not isinstance(text, str):
            msg = "Input text must be a non-empty string."
            raise ValueError(msg)

        if len(text) > self.config.max_input_length:
            msg = f"Input text length ({len(text)}) exceeds maximum allowed ({self.config.max_input_length})."
            raise ValueError(msg)

        logger.info("Starting RAPTOR process: Chunking text.")
        initial_chunks_iter = self.chunker.split_text(text, self.config)

        store_ctx: contextlib.AbstractContextManager[DiskChunkStore] = (
            DiskChunkStore() if store is None else contextlib.nullcontext(store)
        )

        with store_ctx as active_store:
            # Level 0
            clusters, current_level_ids = self._process_level_zero(
                initial_chunks_iter, active_store
            )
            l0_ids = list(current_level_ids)

            # Recursive Summarization
            current_level_ids = self._process_recursion(
                clusters, current_level_ids, active_store
            )

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
        """
        level = start_level
        while True:
            node_count = len(current_level_ids)
            logger.info(f"Processing Level {level}. Node count: {node_count}")

            if node_count <= 1:
                break

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

            is_final = len(clusters) == 1
            strategy = self._get_strategy_for_level(level, is_final)
            logger.info(f"Using strategy {type(strategy).__name__} for Level {level} (Final={is_final})")

            next_level = level + 1
            new_nodes_iter = self._summarize_clusters(clusters, current_level_ids, store, next_level, strategy)

            current_level_ids = []
            summary_buffer: list[SummaryNode] = []
            BATCH_SIZE = self.config.chunk_buffer_size

            for node in new_nodes_iter:
                current_level_ids.append(node.id)
                summary_buffer.append(node)

                if len(summary_buffer) >= BATCH_SIZE:
                    store.add_summaries(summary_buffer)
                    summary_buffer.clear()

            if summary_buffer:
                store.add_summaries(summary_buffer)

            level = next_level

            if len(current_level_ids) > 1:
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
            def node_text_generator() -> Iterator[tuple[NodeID, str]]:
                for nid in current_level_ids:
                    node = store.get_node(nid)
                    if node:
                        yield nid, node.text
                    else:
                        logger.warning(
                            f"Node {nid} not found in store during next level clustering."
                        )

            for batch in batched(node_text_generator(), self.config.embedding_batch_size):
                # Optimize: Don't convert to list if possible, or unzip efficiently.
                # zip(*batch) creates two tuples.
                ids_tuple, texts_tuple = zip(*batch, strict=True)

                if not ids_tuple:
                    continue

                try:
                    embeddings = self.embedder.embed_strings(texts_tuple)
                    for nid, embedding in zip(ids_tuple, embeddings, strict=True):
                        store.update_node_embedding(nid, embedding)
                        yield embedding
                except Exception as e:
                    logger.exception("Failed to embed batch during next level clustering.")
                    msg = "Embedding failed during recursion"
                    raise MatomeError(msg) from e

        try:
            return self.clusterer.cluster_nodes(lx_embedding_generator(), self.config)
        except Exception as e:
            msg = "Clustering failed during recursion"
            raise ClusteringError(msg) from e

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
                 # Empty tree is valid for empty input
                 pass
            msg = "No nodes remaining."
            raise ValueError(msg)

        root_id = current_level_ids[0]
        root_node_obj = store.get_node(root_id)

        if not root_node_obj:
            msg = f"Root node {root_id} not found in store."
            raise ValueError(msg)

        # Ensure root embedding
        if root_node_obj.embedding is None:
            logger.info(f"Generating embedding for root node {root_id}")
            embeddings = list(self.embedder.embed_strings([root_node_obj.text]))
            if embeddings:
                root_node_obj.embedding = embeddings[0]
                store.update_node_embedding(root_id, embeddings[0])

        if isinstance(root_node_obj, Chunk):
            root_node = self._handle_single_chunk_root(root_node_obj, store)
        else:
            root_node = root_node_obj

        return DocumentTree(
            root_node=root_node,
            leaf_chunk_ids=l0_ids,
            metadata={"levels": root_node.level},
        )

    def _handle_single_chunk_root(self, chunk: Chunk, store: DiskChunkStore) -> SummaryNode:
        """Handle case where input text fits in a single chunk."""
        node_id = str(uuid.uuid4())
        strategy = WisdomStrategy()

        summary_text = ""
        try:
             summary_text = self.summarizer.summarize(chunk.text, self.config, strategy)
        except Exception:
             # Fallback to chunk text if summarization fails
             logger.warning("Single chunk summarization failed, falling back to raw text.")
             summary_text = chunk.text

        # Validation
        if not summary_text or not summary_text.strip():
             logger.warning("Summarization produced empty text, falling back to raw chunk.")
             summary_text = chunk.text

        root_node = SummaryNode(
            id=node_id,
            text=summary_text,
            level=1,
            children_indices=[chunk.index],
            metadata=NodeMetadata(
                dikw_level=DIKWLevel.WISDOM,
                type="single_chunk_root"
            ),
        )
        store.add_summaries([root_node])
        return root_node

    def _summarize_clusters(
        self,
        clusters: list[Cluster],
        current_level_ids: list[NodeID],
        store: DiskChunkStore,
        level: int,
        strategy: PromptStrategy,
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
                    continue

                node_id = current_level_ids[idx]
                node = store.get_node(node_id)
                if not node:
                    continue

                children_indices.append(node_id)
                cluster_texts.append(node.text)

            if not cluster_texts:
                continue

            # Validation: Length of combined text
            combined_text_len = sum(len(t) for t in cluster_texts)
            combined_text = "\n\n".join(cluster_texts)

            if combined_text_len > self.config.max_input_length:
                 logger.warning(f"Cluster {cluster.id} text length ({combined_text_len}) exceeds limit. Truncating.")
                 combined_text = combined_text[:self.config.max_input_length]

            try:
                summary_text = self.summarizer.summarize(combined_text, self.config, strategy)
            except SummarizationError:
                logger.exception(f"Summarization failed for cluster {cluster.id}")
                summary_text = "Summarization failed."

            node_id_str = str(uuid.uuid4())

            metadata = NodeMetadata(
                dikw_level=strategy.dikw_level,
                cluster_id=cluster.id
            )

            summary_node = SummaryNode(
                id=node_id_str,
                text=summary_text,
                level=level,
                children_indices=children_indices,
                metadata=metadata,
            )

            yield summary_node
