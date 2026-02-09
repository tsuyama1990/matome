import logging
import uuid
from collections.abc import Iterator
from typing import cast

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree, SummaryNode
from domain_models.types import NodeID
from matome.engines.embedder import EmbeddingService
from matome.interfaces import Chunker, Clusterer, Summarizer

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
        """
        Initialize the RAPTOR engine.

        Args:
            chunker: Service for splitting text into chunks.
            embedder: Service for generating vector embeddings.
            clusterer: Service for clustering nodes.
            summarizer: Service for summarizing text.
            config: Configuration parameters.
        """
        self.chunker = chunker
        self.embedder = embedder
        self.clusterer = clusterer
        self.summarizer = summarizer
        self.config = config

    def _create_summary_nodes(
        self,
        clusters: list[Cluster],
        current_nodes: list[Chunk | SummaryNode],
        level: int,
    ) -> tuple[list[SummaryNode], dict[str, SummaryNode]]:
        """Helper to create summary nodes from clusters."""
        new_nodes: list[SummaryNode] = []
        new_summaries: dict[str, SummaryNode] = {}

        for cluster in clusters:
            children_indices: list[NodeID] = []
            cluster_texts: list[str] = []

            for idx_raw in cluster.node_indices:
                idx = int(idx_raw)
                node = current_nodes[idx]
                if isinstance(node, Chunk):
                    children_indices.append(node.index)
                    cluster_texts.append(node.text)
                else:
                    children_indices.append(node.id)
                    cluster_texts.append(node.text)

            combined_text = "\n\n".join(cluster_texts)
            summary_text = self.summarizer.summarize(combined_text, self.config)

            node_id = str(uuid.uuid4())
            summary_node = SummaryNode(
                id=node_id,
                text=summary_text,
                level=level,
                children_indices=children_indices,
                metadata={"cluster_id": cluster.id},
            )

            new_nodes.append(summary_node)
            new_summaries[node_id] = summary_node

        return new_nodes, new_summaries

    def run(self, text: str) -> DocumentTree:
        """
        Execute the RAPTOR pipeline on the input text.

        Args:
            text: The full input text.

        Returns:
            A DocumentTree containing the hierarchical summary structure.
        """
        # 1. Chunking
        logger.info("Starting RAPTOR process: Chunking text.")
        initial_chunks = self.chunker.split_text(text, self.config)
        if not initial_chunks:
            logger.warning("Input text resulted in no chunks.")
            msg = "Input text is too short or empty to process."
            raise ValueError(msg)

        leaf_chunks: list[Chunk] = []
        current_embeddings_gen: Iterator[list[float]] | None = None

        if len(initial_chunks) > 1:
            # Prepare streaming embedding for L0
            def l0_embedding_generator() -> Iterator[list[float]]:
                for chunk in self.embedder.embed_chunks(initial_chunks):
                    if chunk.embedding is None:
                         msg = f"Chunk {chunk.index} missing embedding."
                         raise ValueError(msg)
                    emb = chunk.embedding
                    yield emb

                    # Store chunk without embedding to save RAM
                    chunk.embedding = None
                    leaf_chunks.append(chunk)

            current_embeddings_gen = l0_embedding_generator()
        else:
            leaf_chunks = initial_chunks

        current_nodes: list[Chunk | SummaryNode] = cast(list[Chunk | SummaryNode], leaf_chunks)
        all_summaries: dict[str, SummaryNode] = {}
        level = 0

        while True:
            node_count = len(initial_chunks) if level == 0 else len(current_nodes)
            logger.info(f"Processing Level {level}. Node count: {node_count}")

            if node_count <= 1:
                break

            clusters = self._perform_clustering_step(level, current_nodes, current_embeddings_gen, node_count)

            # Reset generator after use (it's one-off)
            current_embeddings_gen = None
            if level == 0:
                current_nodes = cast(list[Chunk | SummaryNode], leaf_chunks)

            logger.info(f"Level {level}: Generated {len(clusters)} clusters.")

            # Summarization
            level += 1
            new_level_nodes, new_summaries = self._create_summary_nodes(
                clusters, current_nodes, level
            )
            all_summaries.update(new_summaries)
            current_nodes = cast(list[Chunk | SummaryNode], new_level_nodes)

        # Finalize
        root_node = self._finalize_root(current_nodes)

        if isinstance(root_node, SummaryNode) and root_node.id not in all_summaries:
             all_summaries[root_node.id] = root_node

        logger.info(f"RAPTOR finished. Root ID: {root_node.id}, Levels: {root_node.level}")

        return DocumentTree(
            root_node=root_node,
            all_nodes=all_summaries,
            leaf_chunks=leaf_chunks,
            metadata={"levels": root_node.level},
        )

    def _perform_clustering_step(
        self,
        level: int,
        current_nodes: list[Chunk | SummaryNode],
        current_embeddings_gen: Iterator[list[float]] | None,
        node_count: int
    ) -> list[Cluster]:
        """Execute clustering for the current level."""
        clusters: list[Cluster]

        if level == 0:
            if current_embeddings_gen is None:
                 # Should not happen if logic is correct
                 msg = "Embedding generator missing for Level 0."
                 raise RuntimeError(msg)
            clusters = self.clusterer.cluster_nodes(current_embeddings_gen, self.config)
        else:
            summary_texts = [node.text for node in current_nodes]
            embedding_iter = self.embedder.embed_strings(summary_texts)
            clusters = self.clusterer.cluster_nodes(embedding_iter, self.config)

        # Check for non-reduction
        if len(clusters) == node_count:
            logger.warning(
                f"Clustering at level {level} resulted in {len(clusters)} clusters "
                f"for {node_count} nodes (no reduction). Forcing merge into single cluster."
            )
            clusters = [
                Cluster(
                    id=0,
                    level=level,
                    node_indices=list(range(node_count)),
                )
            ]
        return clusters

    def _finalize_root(self, current_nodes: list[Chunk | SummaryNode]) -> SummaryNode:
        """Handle final state to determine the root node."""
        if len(current_nodes) == 1:
            node = current_nodes[0]
            if isinstance(node, SummaryNode):
                return node
            # Edge Case: Single chunk input.
            chunk = node
            return SummaryNode(
                id=str(uuid.uuid4()),
                text=chunk.text,
                level=1,
                children_indices=[chunk.index],
                metadata={"type": "single_chunk_root"},
            )

        if len(current_nodes) > 1:
            msg = "Unexpected state: Multiple nodes remain after processing."
            raise ValueError(msg)

        msg = "No nodes remaining."
        raise ValueError(msg)
