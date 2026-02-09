import logging
import uuid
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
    ) -> tuple[list[SummaryNode], dict[str, SummaryNode], list[str]]:
        """Helper to create summary nodes from clusters."""
        new_nodes: list[SummaryNode] = []
        new_summaries: dict[str, SummaryNode] = {}
        texts: list[str] = []

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
            texts.append(summary_text)

        return new_nodes, new_summaries, texts

    def run(self, text: str) -> DocumentTree:
        """
        Execute the RAPTOR pipeline on the input text.

        Args:
            text: The full input text.

        Returns:
            A DocumentTree containing the hierarchical summary structure.
        """
        # 1. Chunking (Level 0)
        logger.info("Starting RAPTOR process: Chunking text.")
        initial_chunks = self.chunker.split_text(text, self.config)
        if not initial_chunks:
            logger.warning("Input text resulted in no chunks.")
            msg = "Input text is too short or empty to process."
            raise ValueError(msg)

        # 2. Embedding Level 0
        logger.info(f"Embedding {len(initial_chunks)} chunks.")

        # embed_chunks is a generator that yields chunks with embeddings populated.
        # However, for clustering (step 3), we need random access to embeddings/nodes
        # because the clusterer returns indices, and we need to map those back to nodes.
        # Also, UMAP/GMM clustering algorithms typically require the full dataset
        # to find structure, so full streaming is not feasible for the clustering step itself.
        # We limit memory usage in clustering via memmap, but here we hold objects in memory.
        # For extremely large datasets, this list materialization is a bottleneck.
        # TODO: Future optimization: Store chunks in DB/disk and only hold IDs/Embeddings in memory.
        leaf_chunks = list(self.embedder.embed_chunks(initial_chunks))

        # Prepare for recursion
        current_nodes: list[Chunk | SummaryNode] = cast(list[Chunk | SummaryNode], leaf_chunks)

        # Extract embeddings. Ensure they exist.
        current_embeddings: list[list[float]] = []
        for c in leaf_chunks:
            if c.embedding is None:
                msg = f"Chunk {c.index} missing embedding after embedding step."
                raise ValueError(msg)
            current_embeddings.append(c.embedding)

        all_summaries: dict[str, SummaryNode] = {}
        level = 0

        # Recursion Loop
        while True:
            node_count = len(current_nodes)
            logger.info(f"Processing Level {level}. Node count: {node_count}")

            # Check termination
            if node_count <= 1:
                break

            # 3. Clustering
            clusters = self.clusterer.cluster_nodes(current_embeddings, self.config)

            # Check for non-reduction
            if len(clusters) == node_count:
                logger.warning(
                    f"Clustering at level {level} resulted in {len(clusters)} clusters "
                    f"for {node_count} nodes (no reduction). Forcing merge into single cluster."
                )
                clusters = [
                    Cluster(
                        id=0,  # Temp ID
                        level=level,
                        node_indices=list(range(node_count)),
                    )
                ]

            logger.info(f"Level {level}: Generated {len(clusters)} clusters.")

            # 4. Summarization
            level += 1
            new_level_nodes, new_summaries, texts_to_embed = self._create_summary_nodes(
                clusters, current_nodes, level
            )
            all_summaries.update(new_summaries)

            # 5. Embed New Nodes
            if texts_to_embed:
                new_embeddings = list(self.embedder.embed_strings(texts_to_embed))
            else:
                new_embeddings = []

            # Update State
            current_nodes = cast(list[Chunk | SummaryNode], new_level_nodes)
            current_embeddings = new_embeddings

        # Finalize Root
        root_node = self._finalize_root(current_nodes)

        # If the finalized root wasn't in all_summaries (e.g. wrapped single chunk), add it.
        # Check by ID.
        if isinstance(root_node, SummaryNode) and root_node.id not in all_summaries:
             all_summaries[root_node.id] = root_node

        logger.info(f"RAPTOR finished. Root ID: {root_node.id}, Levels: {root_node.level}")

        return DocumentTree(
            root_node=root_node,
            all_nodes=all_summaries,
            leaf_chunks=leaf_chunks,
            metadata={"levels": root_node.level},
        )

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
            # Should be unreachable if loop works correctly
            msg = "Unexpected state: Multiple nodes remain after processing."
            raise ValueError(msg)

        msg = "No nodes remaining."
        raise ValueError(msg)
