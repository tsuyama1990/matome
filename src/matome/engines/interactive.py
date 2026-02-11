import logging

from domain_models.config import ProcessingConfig
from domain_models.manifest import SummaryNode
from matome.agents.strategies import RefinementStrategy
from matome.engines.embedder import EmbeddingService
from matome.interfaces import Summarizer
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


class InteractiveRaptorEngine:
    """
    Engine for interactive operations on the RAPTOR tree.
    Allows for single-node refinement and traversal.
    """

    def __init__(
        self,
        store: DiskChunkStore,
        summarizer: Summarizer,
        embedder: EmbeddingService,
        config: ProcessingConfig,
    ) -> None:
        """
        Initialize the InteractiveRaptorEngine.

        Args:
            store: The DiskChunkStore containing the tree.
            summarizer: The summarizer agent for refinement.
            embedder: The embedding service for updating vector representations.
            config: Processing configuration.
        """
        self.store = store
        self.summarizer = summarizer
        self.embedder = embedder
        self.config = config

    def refine_node(self, node_id: str, instructions: str) -> SummaryNode:
        """
        Refine a specific node based on user instructions.

        Args:
            node_id: The ID of the node to refine.
            instructions: User instructions for rewriting.

        Returns:
            The updated SummaryNode.

        Raises:
            ValueError: If node is not found.
            TypeError: If node is not a SummaryNode.
        """
        node = self.store.get_node(node_id)
        if not node:
            msg = f"Node {node_id} not found."
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = f"Node {node_id} is a leaf Chunk, not a SummaryNode. Refinement not supported."
            raise TypeError(msg)

        # Use current text as source for refinement.
        source_text = node.text

        strategy = RefinementStrategy(instructions)

        try:
            # We assume summarizer can handle empty context or partial context
            new_text = self.summarizer.summarize(
                source_text,
                self.config,
                level=node.level,
                strategy=strategy,
            )
        except Exception as e:
            msg = f"Failed to refine node {node_id}: {e}"
            logger.exception(msg)
            raise ValueError(msg) from e

        # Update node metadata and text
        node.text = new_text
        node.metadata.is_user_edited = True
        node.metadata.refinement_history.append(instructions)

        # Update embedding
        try:
            # embed_strings returns a generator/iterator
            embeddings = list(self.embedder.embed_strings([new_text]))
            if embeddings:
                new_embedding = embeddings[0]
                node.embedding = new_embedding
                # Persist embedding update explicitly if store separates it
                self.store.update_node_embedding(node_id, new_embedding)
        except Exception as e:
            logger.warning(f"Failed to update embedding for refined node {node_id}: {e}")
            # Non-critical failure? Maybe. But search will be stale.

        # Persist updated node
        # add_summaries uses UPDATE logic usually (UPSERT)
        self.store.add_summaries([node])

        return node
