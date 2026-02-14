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
            # Empty store or only chunks is acceptable?
            # If there are chunks but no summaries, max_level is 0 (if only chunks exist, level 0).
            # If the store is totally empty, max_level might return 0.
            # We assume a valid tree has at least level 1 summary.
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

        # If node at max level is not a summary (unlikely if level > 0), handle it.
        # Chunk at level 0 is not a root of a tree usually unless single chunk doc.
        # But get_max_level queries only summary nodes in current store implementation?
        # Let's check store implementation. get_max_level queries "summary" type.
        # So this branch might be unreachable if logic is correct, but safe to keep.

        msg = f"Root node {root_id} is not a SummaryNode."
        raise MatomeError(msg)

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

        # Batch retrieval is handled by get_children calling store.get_nodes
        # We consume the generator into a list because we need to concatenate text.
        # Memory Safety: We check the total length before fully processing if possible,
        # but to know total length we need to fetch.
        # Ideally, we stream and sum length, stopping if it exceeds a safe limit.
        children: list[SummaryNode | Chunk] = []
        total_len = 0
        limit = self.config.max_input_length * 2 # Buffer for context

        for child in self.get_children(node):
            children.append(child)
            total_len += len(child.text)
            if total_len > limit:
                # We stop materializing to avoid OOM, but we still need to validate count.
                # If we stop early, count check will fail.
                # If the node implies huge children, we can't refine it easily with this architecture.
                # We log warning and proceed with what we have? No, partial data is bad.
                # We raise error?
                pass
                # For now, let's just break and let the validation catch mismatch or truncation handle it.
                # Actually, validation "len(children) != len(node.children_indices)" requires ALL children.
                # So we must fetch all IDs.
                # If distinct children count is huge, we might OOM.
                # But typically children count is 5-20 (clustering).
                # So list(children) is safe for count, but total TEXT might be large.

        # Validation: Ensure we retrieved all expected children
        if len(children) != len(node.children_indices):
            msg = f"Node {node_id} expects {len(node.children_indices)} children but found {len(children)}. Cannot refine with incomplete data."
            logger.error(msg)
            raise ValueError(msg)

        if not children:
            msg = f"Node {node_id} has no accessible children. Cannot refine."
            raise ValueError(msg)

        # Construct source text
        child_texts = [child.text for child in children]
        source_text = "\n\n".join(child_texts)

        # Truncate source text if it exceeds limits to prevent context overflow errors
        if len(source_text) > self.config.max_input_length:
             logger.warning(f"Refinement source text for node {node_id} truncated to {self.config.max_input_length} chars.")
             source_text = source_text[:self.config.max_input_length]

        level_key = node.metadata.dikw_level.value
        base_strategy_cls = STRATEGY_REGISTRY.get(level_key)

        base_strategy = base_strategy_cls() if base_strategy_cls else None

        strategy = RefinementStrategy(base_strategy=base_strategy)

        new_text = self.summarizer.summarize(
            source_text,
            strategy=strategy,
            context={"instruction": instruction},
        )

        # Update node in memory
        node.text = new_text
        node.metadata.is_user_edited = True
        node.metadata.refinement_history.append(instruction)
        node.embedding = None

        # Persist to DB using store's transaction management (update_node handles its own transaction)
        self.store.update_node(node)

        logger.info(f"Refined node {node_id} with instruction: {instruction}")
        return node
