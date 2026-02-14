import contextlib
import logging
import uuid
from collections.abc import Iterable, Iterator
from typing import cast

from domain_models.config import ProcessingConfig
from domain_models.constants import MAX_RECURSION_DEPTH
from domain_models.manifest import Chunk, Cluster, DocumentTree, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel, NodeID
from matome.agents.strategies import (
    STRATEGY_REGISTRY,
    ChainOfDensityStrategy,
    WisdomStrategy,
)
from matome.engines.embedder import EmbeddingService
from matome.exceptions import MatomeError, SummarizationError
from matome.interfaces import Chunker, Clusterer, PromptStrategy, Summarizer
from matome.utils.compat import batched
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


class StopRecursionError(Exception):
    """Internal exception to signal recursion termination with a result."""

    def __init__(self, result_node_id: NodeID) -> None:
        self.result_node_id = result_node_id


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

    def _get_strategy_for_level(self, current_level: int, is_final_layer: bool) -> PromptStrategy:
        """
        Determine the PromptStrategy based on the current level and topology.
        """
        topology_key: str
        if is_final_layer:
            topology_key = "root"
        elif current_level == 0:
            topology_key = "leaf"
        else:
            topology_key = "intermediate"

        target_dikw = self.config.dikw_topology.get(topology_key, DIKWLevel.KNOWLEDGE)

        strategy_name = self.config.strategy_mapping.get(target_dikw, target_dikw.value)

        strategy_class = STRATEGY_REGISTRY.get(strategy_name)
        if strategy_class:
            return strategy_class()

        return ChainOfDensityStrategy()

    def _process_level_zero(
        self, initial_chunks: Iterable[Chunk], store: DiskChunkStore
    ) -> tuple[list[Cluster], int]:
        """
        Handle Level 0: Embedding, Storage, and Clustering.
        Strictly streaming.
        Returns clusters and the count of nodes processed.
        """
        stats = {"node_count": 0}

        def l0_embedding_generator() -> Iterator[tuple[NodeID, list[float]]]:
            try:
                chunk_stream = self.embedder.embed_chunks(initial_chunks)

                for chunk_batch_tuple in batched(chunk_stream, self.config.chunk_buffer_size):
                    store.add_chunks(chunk_batch_tuple)

                    for chunk in chunk_batch_tuple:
                        self._validate_chunk_embedding(chunk)

                        if chunk.embedding is None:
                            continue

                        stats["node_count"] += 1
                        yield (str(chunk.index), chunk.embedding)

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
             raise MatomeError(msg) from e

        return clusters, stats["node_count"]

    def _validate_chunk_embedding(self, chunk: Chunk) -> None:
        """Helper to validate chunk embedding exists."""
        if chunk.embedding is None:
            msg = f"Chunk {chunk.index} missing embedding."
            raise MatomeError(msg)

    def run(self, text: str | Iterable[str], store: DiskChunkStore | None = None) -> DocumentTree:
        """
        Execute the RAPTOR pipeline.
        """
        if not text:
            msg = "Input text cannot be empty."
            raise MatomeError(msg)

        if isinstance(text, str):
            if len(text) > self.config.max_input_length:
                msg = f"Input text length ({len(text)}) exceeds maximum allowed ({self.config.max_input_length})."
                raise MatomeError(msg)
        elif not isinstance(text, Iterable):
            msg = "Input text must be a string or iterable of strings."
            raise MatomeError(msg)

        logger.info("Starting RAPTOR process: Chunking text.")
        initial_chunks_iter = self.chunker.split_text(text, self.config)

        store_ctx: contextlib.AbstractContextManager[DiskChunkStore] = (
            DiskChunkStore() if store is None else contextlib.nullcontext(store)
        )

        with store_ctx as active_store:
            clusters, node_count = self._process_level_zero(
                initial_chunks_iter, active_store
            )

            if node_count == 0:
                 msg = "No nodes remaining."
                 raise MatomeError(msg)

            final_root_id = self._process_recursion(
                clusters, node_count, active_store
            )

            l0_ids = list(active_store.get_node_ids_by_level(0))
            l0_ids_typed = cast(list[NodeID], l0_ids)

            return self._finalize_tree([final_root_id], active_store, l0_ids_typed)

    def _process_recursion(
        self,
        clusters: list[Cluster],
        prev_node_count: int,
        store: DiskChunkStore,
        start_level: int = 0,
    ) -> NodeID:
        """
        Execute the recursive summarization loop.
        """
        level = start_level
        node_count = prev_node_count

        # In the first iteration (Level 0 -> 1), we don't have new IDs yet.
        # But `_process_level_zero` returns clusters based on chunks which are already stored.

        current_level_node_ids: list[NodeID] = []

        while True:
            if level > MAX_RECURSION_DEPTH:
                logger.error(f"Max recursion depth {MAX_RECURSION_DEPTH} exceeded.")
                # Return the first node of current level as a fallback root
                if current_level_node_ids:
                    return current_level_node_ids[0]
                return next(iter(store.get_node_ids_by_level(level)))

            logger.info(f"Processing Level {level}. Node count: {node_count}")

            if node_count == 0:
                msg = f"No nodes found at level {level}"
                raise MatomeError(msg)

            if node_count == 1:
                # If we have only 1 node, it's the root.
                if current_level_node_ids:
                    return current_level_node_ids[0]
                return next(iter(store.get_node_ids_by_level(level)))

            try:
                # If reduction failed, stop recursion with the first available node
                clusters = self._reduce_clusters_if_needed(clusters, node_count, level, store, current_level_node_ids)
            except StopRecursionError as e:
                return e.result_node_id

            is_final = len(clusters) == 1
            logger.info(f"Level {level}: Generated {len(clusters)} clusters.")

            strategy = self._get_strategy_for_level(level, is_final)
            logger.info(f"Using strategy {type(strategy).__name__} for Level {level} (Final={is_final})")

            next_level = level + 1

            # Summarize and get the new node IDs directly
            new_node_ids = self._summarize_and_store_level(
                clusters, store, next_level, strategy
            )

            next_level_count = len(new_node_ids)
            current_level_node_ids = new_node_ids

            level = next_level
            node_count = next_level_count

            # Pass the new IDs to avoid DB query
            clusters = self._embed_and_cluster_next_level(level, store, current_level_node_ids) if node_count > 1 else []

    def _reduce_clusters_if_needed(
        self,
        clusters: list[Cluster],
        node_count: int,
        level: int,
        store: DiskChunkStore,
        current_ids: list[NodeID]
    ) -> list[Cluster]:
        """
        Check if reduction is happening. If not, force reduction or stop.
        """
        if len(clusters) == node_count and node_count > 1:
            logger.warning(
                f"Clustering failed to reduce nodes (Count: {node_count}). Forcing reduction."
            )
            if node_count < 20:
                # Optimization: Use passed IDs if available
                node_ids = current_ids or list(store.get_node_ids_by_level(level))
                return [Cluster(id=0, level=level, node_indices=node_ids)]
            logger.error("Could not reduce nodes. Stopping recursion.")

            # Fallback
            result_id: NodeID
            if current_ids:
                result_id = current_ids[0]
            else:
                result_id = next(iter(store.get_node_ids_by_level(level)))
            raise StopRecursionError(result_id)
        return clusters

    def _summarize_and_store_level(
        self,
        clusters: list[Cluster],
        store: DiskChunkStore,
        output_level: int,
        strategy: PromptStrategy,
    ) -> list[NodeID]:
        """
        Summarize clusters and store the resulting nodes.
        Returns the list of new NodeIDs.
        """
        new_nodes_iter = self._summarize_clusters(
            clusters, store, output_level, strategy
        )

        summary_buffer: list[SummaryNode] = []
        new_ids: list[NodeID] = []

        for node in new_nodes_iter:
            summary_buffer.append(node)
            new_ids.append(node.id)

            if len(summary_buffer) >= self.config.chunk_buffer_size:
                store.add_summaries(summary_buffer)
                summary_buffer.clear()

        if summary_buffer:
            store.add_summaries(summary_buffer)
            summary_buffer.clear()

        return new_ids

    def _embed_and_cluster_next_level(
        self, level: int, store: DiskChunkStore, node_ids: list[NodeID]
    ) -> list[Cluster]:
        """
        Perform embedding and clustering for the next level (summaries).
        Uses cached node_ids to avoid DB scan.
        """

        def lx_embedding_generator() -> Iterator[tuple[NodeID, list[float]]]:
            # Use batched fetch by ID which is efficient in store
            # Need to convert NodeID to str for get_nodes
            str_ids = [str(nid) for nid in node_ids]

            for node in store.get_nodes(str_ids):
                if node:
                    # Yield original ID type if possible, or str.
                    # GMMClusterer handles NodeID (str|int)
                    # SummaryNodes usually have str UUIDs.
                    node_id = node.id if isinstance(node, SummaryNode) else str(node.index)
                    yield (node_id, next(iter(self.embedder.embed_strings([node.text]))))
                else:
                    # Should not happen if consistency is maintained
                    pass

        # Since we need to update embeddings in store too
        # But get_nodes returns objects. We calculate embedding, update object/store, yield.

        # Let's optimize: batch embed
        def batch_embedding_generator() -> Iterator[tuple[NodeID, list[float]]]:
            # Fetch nodes in batches from store is hard if we just have list of IDs.
            # store.get_nodes accepts iterable.
            str_ids = [str(nid) for nid in node_ids]

            # We process in chunks of embedding_batch_size
            for batch_ids in batched(str_ids, self.config.embedding_batch_size):
                nodes = list(store.get_nodes(batch_ids))
                if not nodes:
                    continue

                texts = [n.text for n in nodes]
                embeddings = self.embedder.embed_strings(texts)

                for node, emb in zip(nodes, embeddings, strict=False):
                    # Update store
                    node_id = node.id if isinstance(node, SummaryNode) else str(node.index)
                    store.update_node_embedding(node_id, emb)
                    yield (node_id, emb)

        try:
            return self.clusterer.cluster_nodes(batch_embedding_generator(), self.config)
        except Exception as e:
            msg = "Clustering failed during recursion"
            raise MatomeError(msg) from e

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
            raise MatomeError(msg)

        root_id = current_level_ids[0]
        root_node_obj = store.get_node(root_id)

        if not root_node_obj:
            msg = f"Root node {root_id!s} not found in store."
            raise MatomeError(msg)

        if root_node_obj.embedding is None:
            logger.info(f"Generating embedding for root node {root_id!s}")
            embeddings_iter = self.embedder.embed_strings((root_node_obj.text,))
            try:
                embedding = next(embeddings_iter)
                root_node_obj.embedding = embedding
                store.update_node_embedding(root_id, embedding)
            except StopIteration:
                logger.warning(f"Failed to generate embedding for root node {root_id!s}")

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
        # Use helper for ID generation (UUID)
        node_id = str(uuid.uuid4())
        strategy = WisdomStrategy()

        summary_text = ""
        try:
             summary_text = self.summarizer.summarize(chunk.text, self.config, strategy)
        except Exception:
             logger.warning("Single chunk summarization failed, falling back to raw text.")
             summary_text = chunk.text

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
        store: DiskChunkStore,
        output_level: int,
        strategy: PromptStrategy,
    ) -> Iterator[SummaryNode]:
        """
        Process clusters to generate summaries (streaming).
        """
        for cluster in clusters:
            yield from self._process_single_cluster(
                cluster, store, output_level, strategy
            )

    def _process_single_cluster(
        self,
        cluster: Cluster,
        store: DiskChunkStore,
        output_level: int,
        strategy: PromptStrategy
    ) -> Iterator[SummaryNode]:
        """Process a single cluster."""
        node_ids_in_cluster = cluster.node_indices

        cluster_texts: list[str] = []
        children_indices: list[NodeID] = []
        current_length = 0

        for node in store.get_nodes([str(nid) for nid in node_ids_in_cluster]):
            if not node:
                continue

            text_len = len(node.text)
            if current_length + text_len > self.config.max_input_length:
                 logger.warning(f"Cluster {cluster.id} exceeding max length. Truncating nodes.")
                 break

            children_indices.append(node.index if isinstance(node, Chunk) else node.id)
            cluster_texts.append(node.text)
            current_length += text_len

        if not cluster_texts:
            return

        combined_text = "\n\n".join(cluster_texts)

        if len(combined_text) > self.config.max_input_length:
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
            level=output_level,
            children_indices=children_indices,
            metadata=metadata,
        )

        yield summary_node
