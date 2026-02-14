import logging

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, SummaryNode
from matome.agents.strategies import (
    STRATEGY_REGISTRY,
    RefinementStrategy,
)
from matome.agents.summarizer import SummarizationAgent
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


class InteractiveRaptorEngine:
    """
    Engine for interactive operations on the RAPTOR tree.
    Supports single-node refinement and traversal.
    """

    def __init__(
        self,
        store: DiskChunkStore,
        summarizer: SummarizationAgent,
        config: ProcessingConfig,
    ) -> None:
        self.store = store
        self.summarizer = summarizer
        self.config = config

    def get_node(self, node_id: str | int) -> SummaryNode | Chunk | None:
        """
        Retrieve a node (Summary or Chunk) by its unique ID.
        Delegates to the underlying DiskChunkStore.
        """
        return self.store.get_node(node_id)

    def get_children(self, node: SummaryNode) -> list[SummaryNode | Chunk]:
        """
        Retrieve the immediate children of a given summary node.
        Returns a mixed list of SummaryNodes and Chunks.
        """
        children = []
        for child_idx in node.children_indices:
            child = self.store.get_node(child_idx)
            if child:
                children.append(child)
        return children

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Refine a specific node based on user instruction.
        Re-summarizes the node's children using the instruction as context.
        Updates the node in the store with new text and history.

        Args:
            node_id: ID of the node to refine.
            instruction: User provided refinement instruction.

        Returns:
            The updated SummaryNode.

        Raises:
            ValueError: If node is missing, instruction is empty, or node has no children.
            TypeError: If the node is not a SummaryNode.
        """
        node = self.store.get_node(node_id)
        if not node:
            msg = f"Node {node_id} not found."
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = "Only SummaryNodes can be refined."
            raise TypeError(msg)

        if not instruction:
            msg = "Instruction cannot be empty."
            raise ValueError(msg)

        if len(instruction) > 1000:
            msg = "Instruction exceeds maximum length of 1000 characters."
            raise ValueError(msg)

        # Gather source text from children
        children = self.get_children(node)
        if not children:
            msg = f"Node {node_id} has no accessible children. Cannot refine."
            raise ValueError(msg)

        child_texts = [child.text for child in children]
        source_text = "\n\n".join(child_texts)

        # Determine base strategy from node's DIKW level
        # Assuming the level string matches registry keys (lowercase enum value)
        level_key = node.metadata.dikw_level.value
        base_strategy_cls = STRATEGY_REGISTRY.get(level_key)

        base_strategy = base_strategy_cls() if base_strategy_cls else None

        # Create refinement strategy
        strategy = RefinementStrategy(base_strategy=base_strategy)

        # Execute refinement
        # Note: SummarizationAgent handles prompt formatting with context
        new_text = self.summarizer.summarize(
            source_text,
            strategy=strategy,
            context={"instruction": instruction},
        )

        # Update node
        node.text = new_text
        node.metadata.is_user_edited = True
        node.metadata.refinement_history.append(instruction)

        # Persist changes
        # Re-embedding is optional/deferred for interactivity speed,
        # but spec says "Refinement results are immediately saved".
        # We should clear embedding or update it if we had an embedder here.
        # Since we don't have embedder in this class, we might set it to None.
        # But for now, let's just save the text update.
        node.embedding = None

        # Use add_summaries to update (since it uses INSERT OR REPLACE)
        self.store.add_summary(node)

        logger.info(f"Refined node {node_id} with instruction: {instruction}")
        return node
