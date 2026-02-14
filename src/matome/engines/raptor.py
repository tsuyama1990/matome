import contextlib
import logging
import uuid
from collections.abc import Iterable, Iterator
from typing import cast

from domain_models.config import ProcessingConfig
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
        target_dikw: DIKWLevel
        if is_final_layer:
            target_dikw = DIKWLevel.WISDOM
        elif current_level == 0:
            target_dikw = DIKWLevel.INFORMATION
        else:
            target_dikw = DIKWLevel.KNOWLEDGE

        # Map DIKW level to strategy name using config mapping
        # Config mapping defaults to "wisdom" -> "wisdom" etc.
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

        def l0_embedding_generator() -> Iterator[list[float]]:
            try:
                chunk_stream = self.embedder.embed_chunks(initial_chunks)

                for chunk_batch_tuple in batched(chunk_stream, self.config.chunk_buffer_size):
                    # Keep as tuple, do NOT convert to list to save memory
                    store.add_chunks(chunk_batch_tuple)

                    for chunk in chunk_batch_tuple:
                        self._validate_chunk_embedding(chunk)

                        if chunk.embedding is None:
                            # unreachable due to validate above
                            continue

                        stats["node_count"] += 1
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
             raise MatomeError(msg) from e

        return clusters, stats["node_count"]

    def _validate_chunk_embedding(self, chunk: Chunk) -> None:
        """Helper to validate chunk embedding exists."""
        if chunk.embedding is None:
            msg = f"Chunk {chunk.index} missing embedding."
            raise MatomeError(msg)

    def run(self, text: str, store: DiskChunkStore | None = None) -> DocumentTree:
        """
        Execute the RAPTOR pipeline.
        """
        if not text or not isinstance(text, str):
            msg = "Input text must be a non-empty string."
            raise MatomeError(msg)

        if len(text) > self.config.max_input_length:
            msg = f"Input text length ({len(text)}) exceeds maximum allowed ({self.config.max_input_length})."
            raise MatomeError(msg)

        logger.info("Starting RAPTOR process: Chunking text.")
        initial_chunks_iter = self.chunker.split_text(text, self.config)

        store_ctx: contextlib.AbstractContextManager[DiskChunkStore] = (
            DiskChunkStore() if store is None else contextlib.nullcontext(store)
        )

        with store_ctx as active_store:
            # Level 0
            clusters, node_count = self._process_level_zero(
                initial_chunks_iter, active_store
            )

            if node_count == 0:
                 msg = "No nodes remaining."
                 raise MatomeError(msg)

            # We need L0 IDs for finalizing the tree.
            l0_ids = list(active_store.get_node_ids_by_level(0))
            l0_ids_typed = cast(list[NodeID], l0_ids)

            # Recursive Summarization
            final_root_id = self._process_recursion(
                clusters, node_count, active_store
            )

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
        Returns the ID of the root node.
        """
        level = start_level

        while True:
            # Use count query instead of loading all IDs
            node_count = store.get_node_count(level)
            logger.info(f"Processing Level {level}. Node count: {node_count}")

            if node_count == 0:
                msg = f"No nodes found at level {level}"
                raise MatomeError(msg)

            if node_count == 1:
                # Retrieve the single root ID
                return next(iter(store.get_node_ids_by_level(level)))

            if len(clusters) == node_count and node_count > 1:
                logger.warning(
                    f"Clustering failed to reduce nodes (Count: {node_count}). Forcing reduction."
                )
                if node_count < 20:
                    clusters = [Cluster(id=0, level=level, node_indices=list(range(node_count)))]
                else:
                    logger.error("Could not reduce nodes. Stopping recursion.")
                    return next(iter(store.get_node_ids_by_level(level)))

            logger.info(f"Level {level}: Generated {len(clusters)} clusters.")

            is_final = len(clusters) == 1
            strategy = self._get_strategy_for_level(level, is_final)
            logger.info(f"Using strategy {type(strategy).__name__} for Level {level} (Final={is_final})")

            next_level = level + 1
            # Pass level instead of ID list to support streaming/mapping
            new_nodes_iter = self._summarize_clusters(
                clusters, level, store, next_level, strategy
            )

            summary_buffer: list[SummaryNode] = []

            for node in new_nodes_iter:
                summary_buffer.append(node)

                if len(summary_buffer) >= self.config.chunk_buffer_size:
                    store.add_summaries(summary_buffer)
                    summary_buffer.clear()

            if summary_buffer:
                store.add_summaries(summary_buffer)

            level = next_level

            # Check next level count
            node_count = store.get_node_count(level)

            clusters = self._embed_and_cluster_next_level(level, store) if node_count > 1 else []

        # Should be unreachable if logic is correct, but safe fallback
        ids_iter = store.get_node_ids_by_level(level)
        try:
            return next(iter(ids_iter))
        except StopIteration as e:
             msg = "Recursion ended with no root."
             raise MatomeError(msg) from e

    def _embed_and_cluster_next_level(
        self, level: int, store: DiskChunkStore
    ) -> list[Cluster]:
        """
        Perform embedding and clustering for the next level (summaries).
        Streams IDs from store to avoid loading all into memory.
        """

        def lx_embedding_generator() -> Iterator[list[float]]:
            def node_text_generator() -> Iterator[tuple[NodeID, str]]:
                # Stream IDs directly from store
                for nid in store.get_node_ids_by_level(level):
                    node = store.get_node(nid)
                    if node:
                        yield nid, node.text
                    else:
                        logger.warning(
                            f"Node {nid} not found in store during next level clustering."
                        )

            # Ensure batch size is reasonable
            batch_size = min(self.config.embedding_batch_size, 100)

            for batch in batched(node_text_generator(), batch_size):
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
                 # Empty tree is valid for empty input
                 pass
            msg = "No nodes remaining."
            raise MatomeError(msg)

        root_id = current_level_ids[0]
        root_node_obj = store.get_node(root_id)

        if not root_node_obj:
            msg = f"Root node {root_id} not found in store."
            raise MatomeError(msg)

        # Ensure root embedding
        if root_node_obj.embedding is None:
            logger.info(f"Generating embedding for root node {root_id}")
            # Use generator to avoid list creation even for single item
            embeddings_iter = self.embedder.embed_strings((root_node_obj.text,))
            try:
                embedding = next(embeddings_iter)
                root_node_obj.embedding = embedding
                store.update_node_embedding(root_id, embedding)
            except StopIteration:
                logger.warning(f"Failed to generate embedding for root node {root_id}")

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

    def _create_index_map(
        self, clusters: list[Cluster], input_level: int, store: DiskChunkStore
    ) -> dict[int, NodeID]:
        """
        Create a mapping from cluster node indices to actual NodeIDs.
        Streams IDs from the store to avoid loading all IDs into memory.
        """
        needed_indices = set()
        for cluster in clusters:
            for idx_raw in cluster.node_indices:
                needed_indices.add(int(idx_raw))

        sorted_needed_indices = sorted(needed_indices)
        index_to_id: dict[int, NodeID] = {}

        if not sorted_needed_indices:
            return index_to_id

        needed_ptr = 0
        for current_idx, node_id in enumerate(store.get_node_ids_by_level(input_level)):
            if needed_ptr >= len(sorted_needed_indices):
                break

            target_idx = sorted_needed_indices[needed_ptr]

            if current_idx == target_idx:
                index_to_id[target_idx] = node_id
                needed_ptr += 1
                while needed_ptr < len(sorted_needed_indices) and sorted_needed_indices[needed_ptr] == current_idx:
                     needed_ptr += 1

        return index_to_id

    def _summarize_clusters(
        self,
        clusters: list[Cluster],
        input_level: int,
        store: DiskChunkStore,
        output_level: int,
        strategy: PromptStrategy,
    ) -> Iterator[SummaryNode]:
        """
        Process clusters to generate summaries (streaming).
        Builds a map of referenced IDs to avoid loading all IDs.
        """
        index_to_id = self._create_index_map(clusters, input_level, store)

        # 3. Summarize using the map, processing in batches to avoid OOM
        # Batch size for processing clusters
        CLUSTER_BATCH_SIZE = 20

        for cluster_batch in batched(clusters, CLUSTER_BATCH_SIZE):
            yield from self._process_cluster_batch(
                cluster_batch, index_to_id, store, output_level, strategy
            )

    def _process_cluster_batch(
        self,
        cluster_batch: tuple[Cluster, ...],
        index_to_id: dict[int, NodeID],
        store: DiskChunkStore,
        output_level: int,
        strategy: PromptStrategy,
    ) -> Iterator[SummaryNode]:
        """Helper to process a batch of clusters."""
        batch_node_ids = []
        cluster_node_map: dict[NodeID, list[NodeID]] = {}

        # Collect IDs for this batch
        for cluster in cluster_batch:
            ids_for_cluster = []
            for idx_raw in cluster.node_indices:
                idx = int(idx_raw)
                nid = index_to_id.get(idx)
                if nid is not None:
                    ids_for_cluster.append(nid)

            cluster_node_map[cluster.id] = ids_for_cluster
            batch_node_ids.extend(ids_for_cluster)

        # Fetch nodes for this batch only
        fetched_nodes_list = list(store.get_nodes([str(nid) for nid in batch_node_ids]))
        fetched_node_lookup = {
            str(n.index if isinstance(n, Chunk) else n.id): n
            for n in fetched_nodes_list if n
        }

        # Process clusters in this batch
        for cluster in cluster_batch:
            yield from self._generate_summary_for_cluster(
                cluster, cluster_node_map, fetched_node_lookup, output_level, strategy
            )

    def _generate_summary_for_cluster(
        self,
        cluster: Cluster,
        cluster_node_map: dict[NodeID, list[NodeID]],
        fetched_node_lookup: dict[str, Chunk | SummaryNode],
        output_level: int,
        strategy: PromptStrategy,
    ) -> Iterator[SummaryNode]:
        """Generate a summary node for a single cluster."""
        children_indices: list[NodeID] = []
        cluster_texts: list[str] = []

        current_length = 0

        needed_ids = cluster_node_map.get(cluster.id, [])

        for nid_ref in needed_ids:
            node = fetched_node_lookup.get(str(nid_ref))
            if not node:
                continue

            text_len = len(node.text)
            if current_length + text_len > self.config.max_input_length:
                 logger.warning(f"Cluster {cluster.id} exceeding max length. Truncating nodes.")
                 break

            children_indices.append(nid_ref)
            cluster_texts.append(node.text)
            current_length += text_len

        if not cluster_texts:
            return

        combined_text = "\n\n".join(cluster_texts)

        # Additional safety check for total length after join (headers etc)
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
