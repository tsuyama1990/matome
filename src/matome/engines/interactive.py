import logging
from typing import Any

from domain_models.config import ProcessingConfig
from domain_models.manifest import SummaryNode
from matome.agents.strategies import RefinementStrategy
from matome.agents.summarizer import SummarizationAgent
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


class InteractiveRaptorEngine:
    """
    Engine for interactive refinement and modification of the DIKW tree.
    Wraps DiskChunkStore and SummarizationAgent to handle single-node updates.
    """

    def __init__(
        self,
        store: DiskChunkStore,
        agent: SummarizationAgent,
        config: ProcessingConfig,
    ) -> None:
        self.store = store
        self.agent = agent
        self.config = config

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Refine a specific node based on user instruction.

        Args:
            node_id: The ID of the node to refine.
            instruction: The user's instruction for refinement.

        Returns:
            The updated SummaryNode.

        Raises:
            ValueError: If node not found or is a Chunk (cannot refine raw chunks yet).
        """
        node = self.store.get_node(node_id)
        if not node:
            msg = f"Node {node_id} not found."
            logger.error(msg)
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = f"Cannot refine raw Chunk {node_id}. Only SummaryNodes are supported."
            logger.error(msg)
            raise TypeError(msg)

        logger.info(f"Refining node {node_id} with instruction: {instruction}")

        # Create RefinementStrategy
        strategy = RefinementStrategy(instruction)

        try:
            # We pass the current node text as "text" to summarize.
            # The strategy will format it with instruction.
            # We inject the strategy directly into the existing agent.
            new_text = self.agent.summarize(node.text, level=node.level, strategy=strategy)
        except Exception:
            logger.exception(f"Refinement failed for node {node_id}")
            raise

        # Update node content
        node.text = new_text

        # Update metadata
        node.metadata.is_user_edited = True
        node.metadata.refinement_history.append(instruction)

        # Persist to store
        # DiskChunkStore.add_summary handles updates if ID exists (REPLACE logic)
        self.store.add_summary(node)

        logger.info(f"Node {node_id} refined successfully.")
        return node

    def get_tree_structure(self) -> dict[str, Any]:
        """
        Retrieve the tree structure for visualization.
        Starting from root (Wisdom/L3+), down to leaves.

        This is a placeholder for the GUI logic to traverse the tree.
        """
        # Ideally, we query the store for root nodes.
        # But DiskChunkStore doesn't index roots easily yet.
        # This might be an optimization for later.
        # For now, we assume the caller knows the root or we scan.
        return {}
