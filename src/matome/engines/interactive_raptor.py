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
        summarizer: SummarizationAgent | None,
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

        Returns:
            list[SummaryNode | Chunk]: The immediate children of the given node.
        """
        # Batch retrieve children for efficiency (avoid N+1)
        # children_indices is a list of node IDs.
        # Ensure IDs are strings as expected by get_nodes
        child_ids = [str(idx) for idx in node.children_indices]

        # get_nodes returns a generator, consume it into a list
        # Filter out None values in case of data inconsistency
        children = []
        for child in self.store.get_nodes(child_ids):
            if child is not None:
                children.append(child)

        return children

    def get_root_node(self) -> SummaryNode | None:
        """
        Retrieve the root node of the tree.
        Assumes the root is the (single) node at the highest level.
        """
        max_level = self.store.get_max_level()
        if max_level == 0:
            return None

        # Get nodes at max level
        # store.get_node_ids_by_level returns iterator of IDs
        # We assume there is only one root at the max level, or we just pick the first one.
        ids_iter = self.store.get_node_ids_by_level(max_level)
        try:
            root_id = next(ids_iter)
        except StopIteration:
            return None

        node = self.store.get_node(root_id)
        if isinstance(node, SummaryNode):
            return node

        # If for some reason it's a chunk (shouldn't happen given get_max_level checks summaries), ignore
        return None

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
            RuntimeError: If summarizer agent is not initialized.
        """
        if self.summarizer is None:
            msg = "Summarizer agent is not initialized. Cannot refine node."
            raise RuntimeError(msg)

        node = self.store.get_node(node_id)
        if not node:
            msg = f"Node {node_id} not found."
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = "Only SummaryNodes can be refined."
            raise TypeError(msg)

        if not instruction or not instruction.strip():
            msg = "Instruction cannot be empty."
            raise ValueError(msg)

        max_len = self.config.max_instruction_length
        if len(instruction) > max_len:
            msg = f"Instruction exceeds maximum length of {max_len} characters."
            raise ValueError(msg)

        # Gather source text from children
        children = self.get_children(node)
        if not children:
            msg = f"Node {node_id} has no accessible children. Cannot refine."
            raise ValueError(msg)

        # Validate that we retrieved all expected children
        if len(children) != len(node.children_indices):
            msg = f"Node {node_id} expects {len(node.children_indices)} children but found {len(children)}. Cannot refine with incomplete data."
            logger.error(msg)
            raise ValueError(msg)

        child_texts = [child.text for child in children]
        source_text = "\n\n".join(child_texts)

        # Determine base strategy from node's DIKW level
        # Use enum value directly for lookup
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

        # Wrap update logic in transaction
        with self.store.transaction():
            # Update node fields
            node.text = new_text
            node.metadata.is_user_edited = True
            node.metadata.refinement_history.append(instruction)

            # Re-embedding is optional/deferred for interactivity speed.
            node.embedding = None

            # Persist changes using update_node
            self.store.update_node(node)

        logger.info(f"Refined node {node_id} with instruction: {instruction}")
        return node
