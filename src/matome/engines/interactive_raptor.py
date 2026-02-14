import logging
from collections.abc import Iterator

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, SummaryNode
from matome.agents.strategies import (
    STRATEGY_REGISTRY,
    RefinementStrategy,
)
from matome.agents.summarizer import SummarizationAgent
from matome.exceptions import MatomeError
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

    def get_children(self, node: SummaryNode) -> Iterator[SummaryNode | Chunk]:
        """
        Retrieve the immediate children of a given summary node.
        Returns an iterator to support streaming processing.

        Returns:
            Iterator[SummaryNode | Chunk]: The immediate children of the given node.
        """
        # Batch retrieve children for efficiency (avoid N+1)
        # children_indices is a list of node IDs.
        # Ensure IDs are strings as expected by get_nodes
        child_ids = [str(idx) for idx in node.children_indices]

        # get_nodes returns a generator and fetches in batches
        for child in self.store.get_nodes(child_ids):
            if child is not None:
                yield child

    def get_root_node(self) -> SummaryNode | None:
        """
        Retrieve the root node of the tree.
        Assumes the root is the (single) node at the highest level.

        Raises:
            MatomeError: If the tree structure is invalid (e.g. max level exists but no root).
        """
        max_level = self.store.get_max_level()
        if max_level == 0:
            # Empty store or only chunks is acceptable
            return None

        # Get nodes at max level
        ids_iter = self.store.get_node_ids_by_level(max_level)
        try:
            root_id = next(ids_iter)
        except StopIteration:
            msg = f"Max level is {max_level} but no nodes found at this level."
            logger.exception(msg)
            raise MatomeError(msg) from None

        node = self.store.get_node(root_id)
        if isinstance(node, SummaryNode):
            return node

        msg = f"Root node {root_id} is not a SummaryNode."
        raise MatomeError(msg)

    def _validate_refinement_input(self, node_id: str, instruction: str) -> SummaryNode:
        """Validate input parameters for node refinement."""
        if self.summarizer is None:
            msg = "Summarizer agent is not initialized. Cannot refine node."
            raise RuntimeError(msg)

        if not instruction or not instruction.strip():
            msg = "Instruction cannot be empty."
            raise ValueError(msg)

        max_len = self.config.max_instruction_length
        if len(instruction) > max_len:
            msg = f"Instruction exceeds maximum length of {max_len} characters."
            raise ValueError(msg)

        node = self.store.get_node(node_id)
        if not node:
            msg = f"Node {node_id} not found."
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = "Only SummaryNodes can be refined."
            raise TypeError(msg)

        return node

    def _retrieve_and_validate_children_content(self, node: SummaryNode) -> str:
        """
        Retrieve children, validate count, and concatenate content safely.
        Returns the concatenated source text.
        """
        limit = self.config.max_input_length * 2  # Buffer factor for context (should be in config)
        current_len = 0
        children_count = 0
        child_texts: list[str] = []

        # Stream children to avoid memory issues with huge trees
        for child in self.get_children(node):
            children_count += 1
            text_len = len(child.text)

            # Check length limit before appending
            if current_len + text_len > limit:
                logger.warning(
                    f"Refinement source text for node {node.id} exceeds safety limit ({limit}). Truncating."
                )
                break

            child_texts.append(child.text)
            current_len += text_len

        # Validate count if we didn't truncate (if we truncated, count might mismatch, which is expected)
        # But we must ensure we found *at least* the children we expected if they fit.
        # Actually, if we truncate, we can't validate exact count based on iterator consumption.
        # But we should check if we got NOTHING.
        if children_count == 0:
             msg = f"Node {node.id} has no accessible children. Cannot refine."
             raise ValueError(msg)

        # Ideally check exact count if not truncated, but get_children filters None.
        # For strict data integrity:
        if children_count != len(node.children_indices) and current_len <= limit:
             # This might trigger on truncation too.
             # We should rely on store consistency.
             # If we haven't reached limit but count mismatches, it's an error.
             msg = f"Node {node.id} expects {len(node.children_indices)} children but found {children_count}."
             logger.error(msg)
             raise ValueError(msg)

        return "\n\n".join(child_texts)

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
        """
        node = self._validate_refinement_input(node_id, instruction)
        source_text = self._retrieve_and_validate_children_content(node)

        # Truncate source text if it exceeds limits to prevent context overflow errors
        if len(source_text) > self.config.max_input_length:
             logger.warning(f"Refinement source text for node {node_id} truncated to {self.config.max_input_length} chars.")
             source_text = source_text[:self.config.max_input_length]

        level_key = node.metadata.dikw_level.value
        base_strategy_cls = STRATEGY_REGISTRY.get(level_key)
        base_strategy = base_strategy_cls() if base_strategy_cls else None
        strategy = RefinementStrategy(base_strategy=base_strategy)

        # Summarize (mockable interaction)
        # self.summarizer check is done in _validate_refinement_input
        # but mypy might not know.
        if self.summarizer is None:
            # Should be unreachable due to validation
            msg = "Summarizer not initialized"
            raise RuntimeError(msg)

        new_text = self.summarizer.summarize(
            source_text,
            strategy=strategy,
            context={"instruction": instruction},
        )

        # Transactional update
        with self.store.transaction():
            node.text = new_text
            node.metadata.is_user_edited = True
            node.metadata.refinement_history.append(instruction)
            node.embedding = None
            self.store.update_node(node)

        logger.info(f"Refined node {node_id} with instruction: {instruction}")
        return node
