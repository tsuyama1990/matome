import logging
from typing import Any

from domain_models.config import ProcessingConfig
from domain_models.manifest import SummaryNode
from domain_models.types import NodeID
from matome.agents.strategies import RefinementStrategy
from matome.engines.embedder import EmbeddingService
from matome.interfaces import Summarizer
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


class InteractiveRaptorEngine:
    """
    Engine for interactive refinement of the RAPTOR tree.
    Allows for single-node updates based on user instructions.
    """

    def __init__(
        self,
        summarizer: Summarizer,
        embedder: EmbeddingService,
        config: ProcessingConfig,
    ) -> None:
        """
        Initialize the InteractiveRaptorEngine.

        Args:
            summarizer: The summarization agent.
            embedder: Service for re-embedding nodes.
            config: Processing configuration.
        """
        self.summarizer = summarizer
        self.embedder = embedder
        self.config = config

    def refine_node(
        self, node_id: NodeID, instruction: str, store: DiskChunkStore
    ) -> SummaryNode:
        """
        Refine a specific node based on user instructions.

        Args:
            node_id: The ID of the node to refine.
            instruction: The user's refinement instruction.
            store: The persistent store containing the node.

        Returns:
            The updated SummaryNode.

        Raises:
            ValueError: If the node is not found or is a Chunk (cannot refine raw data).
        """
        # 1. Fetch Node
        node = store.get_node(node_id)
        if not node:
            msg = f"Node {node_id} not found."
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = "Cannot refine raw data chunks. Only summary nodes can be refined."
            raise TypeError(msg)

        # 2. Refine using LLM
        # We use RefinementStrategy
        strategy = RefinementStrategy()
        context: dict[str, Any] = {"instruction": instruction}

        logger.info(f"Refining node {node_id} with instruction: {instruction}")

        # Original text is passed as input
        new_text = self.summarizer.summarize(
            text=node.text,
            config=self.config,
            strategy=strategy,
            context=context,
        )

        # 3. Update Node Metadata
        node.text = new_text
        node.metadata.is_user_edited = True
        node.metadata.refinement_history.append(instruction)

        # 4. Re-embed
        # embed_strings returns an iterator, we take the first item
        try:
            embeddings = list(self.embedder.embed_strings([new_text]))
            if embeddings:
                node.embedding = embeddings[0]
            else:
                 # Should not happen if embedder works correctly
                msg = "Embedder returned no embeddings."
                raise RuntimeError(msg)  # noqa: TRY301
        except Exception:
            logger.exception(f"Failed to re-embed refined node {node_id}")
            # Raise error to ensure consistency
            raise

        # 5. Save to Store
        # We use add_summary which uses "OR REPLACE" logic in store
        store.add_summary(node)

        logger.info(f"Node {node_id} refined and updated successfully.")
        return node
