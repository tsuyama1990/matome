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

        Consumes the initial chunks iterator, embeds them, stores them in the database,
        and then clusters the embeddings. All operations are strictly streaming.
        """
        current_level_ids: list[NodeID] = []
        # Use mutable container to track count within generator
        stats = {"node_count": 0}

        def chunk_storage_generator(chunks: Iterator[Chunk]) -> Iterator[Chunk]:
            """
            Intermediate generator that stores chunks as they pass through.
            DiskChunkStore.add_chunks handles batching internally if we pass a generator?
            Actually, add_chunks takes Iterable. We can't yield and consume at same time easily.

            Strategy: We yield chunks to add_chunks. But wait, we need to embed first.
            EmbeddingService.embed_chunks yields chunks with embeddings.

            So: initial -> embedder -> storage -> yield embedding for clustering.
            """
            # We buffer slightly here to batch writes effectively if store doesn't buffer enough?
            # store.add_chunks implementation: iterates in batches.
            # So if we call store.add_chunks(generator), it consumes generator.
            # But we need to yield embeddings to clusterer *after* (or during) storage.
            # We can't consume generator twice.
            # So we must drive the loop manually.
            yield from chunks

        def l0_embedding_generator() -> Iterator[list[float]]:
            # We must yield embeddings for the clusterer.
            # While doing so, we save to DB.

            # Streaming chain:
            # 1. initial_chunks (Iterator)
            # 2. embedder.embed_chunks (Iterator) -> Yields Chunk with embedding

            chunk_stream = self.embedder.embed_chunks(initial_chunks)

            # We assume store.add_chunks handles lists efficiently.
            # But to strictly stream, we should batch manually here and call store.add_chunks on batches.

            # Using batched to process small groups of chunks
            for chunk_batch_tuple in batched(chunk_stream, self.config.chunk_buffer_size):
                chunk_batch = list(chunk_batch_tuple)

                # 1. Store batch
                store.add_chunks(chunk_batch)

                # 2. Yield embeddings and collect IDs
                for chunk in chunk_batch:
                    if chunk.embedding is None:
                        msg = f"Chunk {chunk.index} missing embedding."
                        raise ValueError(msg)

                    stats["node_count"] += 1
                    current_level_ids.append(chunk.index)
                    yield chunk.embedding

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
            # We process in batches to avoid loading all texts.
            # batch is a tuple of (NodeID, str) tuples.
            # batched is lazy, so we don't load everything.
            for batch in batched(node_text_generator(), self.config.embedding_batch_size):
                # batch is tuple of (id, text)
                ids_iter = (item[0] for item in batch)
                texts_iter = (item[1] for item in batch)

                # To efficiently use embed_strings (which batches internally too, but expects iterable),
                # we can pass the texts iterator.
                # However, we need to zip results with IDs.
                # We need to materialize ids for zipping if we pass iterator to embedder?
                # embed_strings returns iterator.
                # It's safer to materialize this small batch of IDs and Texts to ensure alignment.
                # Since batch size is small (e.g. 32), this is safe.

                ids = list(ids_iter)
                texts = list(texts_iter)

                # Embed batch (returns iterator)
                try:
                    embeddings = self.embedder.embed_strings(texts)
                    for nid, embedding in zip(ids, embeddings, strict=True):
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

        Builds the tree structure from the final root node down to the leaf chunks.
        """
        if not current_level_ids:
            # If input was empty?
            if not l0_ids:
                # Should return empty tree if no chunks at all
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
