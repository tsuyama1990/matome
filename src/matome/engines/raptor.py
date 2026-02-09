import logging
import uuid
from collections.abc import Iterator

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree, SummaryNode
from domain_models.types import NodeID
from matome.engines.embedder import EmbeddingService
from matome.interfaces import Chunker, Clusterer, Summarizer
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

    def _process_level_zero(self, initial_chunks: list[Chunk], store: DiskChunkStore) -> tuple[list[Cluster], list[NodeID]]:
        """Handle Level 0: Embedding, Storage, and Clustering."""
        current_level_ids: list[NodeID] = []

        def l0_embedding_generator() -> Iterator[list[float]]:
            for chunk in self.embedder.embed_chunks(initial_chunks):
                if chunk.embedding is None:
                        msg = f"Chunk {chunk.index} missing embedding."
                        raise ValueError(msg)

                yield chunk.embedding

                # Store chunk (without embedding)
                store_chunk = chunk.model_copy()
                store_chunk.embedding = None
                store.add_chunk(store_chunk)
                current_level_ids.append(store_chunk.index)

        if len(initial_chunks) > 1:
            clusters = self.clusterer.cluster_nodes(l0_embedding_generator(), self.config)
        else:
            c = initial_chunks[0]
            store.add_chunk(c)
            current_level_ids.append(c.index)
            clusters = []

        return clusters, current_level_ids

    def run(self, text: str) -> DocumentTree:
        """Execute the RAPTOR pipeline."""
        logger.info("Starting RAPTOR process: Chunking text.")
        initial_chunks = self.chunker.split_text(text, self.config)
        if not initial_chunks:
            msg = "Input text is too short or empty to process."
            raise ValueError(msg)

        all_summaries: dict[str, SummaryNode] = {}

        with DiskChunkStore() as store:
            # Level 0
            clusters, current_level_ids = self._process_level_zero(initial_chunks, store)
            store.commit()

            level = 0
            while True:
                node_count = len(current_level_ids)
                logger.info(f"Processing Level {level}. Node count: {node_count}")

                if node_count <= 1:
                    break

                if len(clusters) == node_count:
                     clusters = [Cluster(id=0, level=level, node_indices=list(range(node_count)))]

                logger.info(f"Level {level}: Generated {len(clusters)} clusters.")

                # Summarization
                level += 1
                new_nodes, new_summaries = self._summarize_clusters(clusters, current_level_ids, store, level)

                current_level_ids = []
                for node in new_nodes:
                    store.add_summary(node)
                    all_summaries[node.id] = node
                    current_level_ids.append(node.id)
                store.commit()

                if len(current_level_ids) > 1:
                    clusters = self._next_level_clustering(current_level_ids, store)
                else:
                    clusters = []

            return self._finalize_tree(current_level_ids, store, all_summaries, initial_chunks)

    def _next_level_clustering(self, current_level_ids: list[NodeID], store: DiskChunkStore) -> list[Cluster]:
        """Perform embedding and clustering for the next level (summaries)."""
        def lx_embedding_generator() -> Iterator[list[float]]:
            def text_gen() -> Iterator[str]:
                for nid in current_level_ids:
                    node = store.get_node(nid)
                    if node:
                        yield node.text
            yield from self.embedder.embed_strings(text_gen())

        return self.clusterer.cluster_nodes(lx_embedding_generator(), self.config)

    def _finalize_tree(self, current_level_ids: list[NodeID], store: DiskChunkStore, all_summaries: dict[str, SummaryNode], initial_chunks: list[Chunk]) -> DocumentTree:
        """Construct the final DocumentTree."""
        if not current_level_ids:
             msg = "No nodes remaining."
             raise ValueError(msg)

        root_id = current_level_ids[0]
        root_node_obj = store.get_node(root_id)

        if not root_node_obj:
             msg = "Root node not found in store."
             raise ValueError(msg)

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
            leaf_chunks=initial_chunks,
            metadata={"levels": root_node.level},
        )

    def _summarize_clusters(
        self,
        clusters: list[Cluster],
        current_level_ids: list[NodeID],
        store: DiskChunkStore,
        level: int,
    ) -> tuple[list[SummaryNode], dict[str, SummaryNode]]:
        """Process clusters to generate summaries."""
        new_nodes: list[SummaryNode] = []
        new_summaries: dict[str, SummaryNode] = {}

        for cluster in clusters:
            children_indices: list[NodeID] = []
            cluster_texts: list[str] = []

            for idx_raw in cluster.node_indices:
                idx = int(idx_raw)
                node_id = current_level_ids[idx]
                node = store.get_node(node_id)
                if not node:
                    continue

                children_indices.append(node_id)
                cluster_texts.append(node.text)

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

            new_nodes.append(summary_node)
            new_summaries[node_id_str] = summary_node

        return new_nodes, new_summaries
