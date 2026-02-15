import logging
from collections.abc import Iterator

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, SummaryNode
from domain_models.types import NodeID
from matome.agents.strategies import (
    STRATEGY_REGISTRY,
    RefinementStrategy,
)
from matome.agents.summarizer import SummarizationAgent
from matome.exceptions import MatomeError, RefinementError, StoreError
from matome.utils.store import DiskChunkStore
from matome.utils.traversal import traverse_source_chunks
from matome.utils.validation import sanitize_instruction, validate_node_id

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

    def get_node(self, node_id: NodeID) -> SummaryNode | Chunk | None:
        """
        Retrieve a node (Summary or Chunk) by its unique ID.
        Delegates to the underlying DiskChunkStore.
        """
        try:
            return self.store.get_node(node_id)
        except (StoreError, ValueError):
            logger.exception(f"Failed to retrieve node {node_id}")
            raise

    def get_source_chunks(self, node_id: NodeID, limit: int | None = None) -> Iterator[Chunk]:
        """
        Retrieves all original text chunks that contributed to this summary node.
        Performs a streaming traversal down to Level 0.

        Args:
            node_id: The ID of the node to trace.
            limit: Optional maximum number of chunks to yield.

        Yields:
            Chunk: Original source chunks.
        """
        try:
            node = self.store.get_node(node_id)
        except (StoreError, ValueError):
            logger.exception(f"Failed to retrieve node {node_id} for source tracing")
            return

        if not node:
            return

        if isinstance(node, Chunk):
            yield node
            return

        yield from traverse_source_chunks(
            self.store, node, limit, self.config.traversal_max_queue_size
        )

    def get_children(self, node: SummaryNode) -> Iterator[SummaryNode | Chunk]:
        """
        Retrieve the immediate children of a given summary node.
        Returns an iterator to support streaming processing.

        Returns:
            Iterator[SummaryNode | Chunk]: The immediate children of the given node.
        """
        child_ids = node.children_indices

        try:
            for child in self.store.get_nodes(child_ids):
                if child is not None:
                    yield child
        except (StoreError, ValueError):
            logger.exception(f"Failed to retrieve children for node {node.id}")
            raise

    def get_root_node(self) -> SummaryNode | None:
        """
        Retrieve the root node of the tree.
        Assumes the root is the (single) node at the highest level.

        Raises:
            MatomeError: If the tree structure is invalid (e.g. max level exists but no root).
        """
        try:
            return self._get_root_node_internal()
        except (StoreError, ValueError):
            logger.exception("Failed to retrieve root node")
            raise

    def _get_root_node_internal(self) -> SummaryNode | None:
        """Internal helper for root node retrieval."""
        max_level = self.store.get_max_level()
        if max_level == 0:
            return None

        ids_iter = self.store.get_node_ids_by_level(max_level)
        try:
            root_id = next(ids_iter)
        except StopIteration:
            msg = f"Max level is {max_level} but no nodes found at this level."
            raise MatomeError(msg) from None

        node = self.store.get_node(root_id)
        if isinstance(node, SummaryNode):
            return node

        msg = f"Root node {root_id} is not a SummaryNode."
        raise MatomeError(msg)

    def _validate_node(self, node_id: str) -> SummaryNode:
        """Helper to retrieve and validate a SummaryNode exists."""
        try:
            node = self.store.get_node(node_id)
        except (StoreError, ValueError):
            logger.exception(f"Database error retrieving node {node_id}")
            raise

        if not node:
            msg = f"Node {node_id} not found."
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = "Only SummaryNodes can be refined."
            raise TypeError(msg)

        return node

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

        return self._validate_node(node_id)

    def _retrieve_children_content(self, node: SummaryNode) -> tuple[str, int, int]:
        """
        Stream children and collect text efficiently.
        Returns: (concatenated text, total length, number of children processed)
        """
        limit = self.config.max_input_length * self.config.refinement_context_limit_multiplier
        current_len = 0
        child_count = 0
        parts: list[str] = []

        try:
            for child in self.get_children(node):
                text_len = len(child.text)
                if current_len + text_len > limit:
                    logger.warning(
                        f"Refinement source text for node {node.id} exceeds safety limit ({limit}). Truncating."
                    )
                    break
                parts.append(child.text)
                current_len += text_len
                child_count += 1
        except (StoreError, ValueError):
            logger.exception(f"Error retrieving children content for node {node.id}")
            raise

        return "\n\n".join(parts), current_len, child_count

    def _retrieve_and_validate_children_content(self, node: SummaryNode) -> str:
        """
        Retrieve children, validate count, and concatenate content safely.
        Returns the concatenated source text.
        """
        source_text, current_len, children_count = self._retrieve_children_content(node)

        if children_count == 0:
             msg = f"Node {node.id} has no accessible children. Cannot refine."
             raise ValueError(msg)

        limit = self.config.max_input_length * self.config.refinement_context_limit_multiplier
        if children_count != len(node.children_indices) and current_len <= limit:
             msg = f"Node {node.id} expects {len(node.children_indices)} children but found {children_count}."
             logger.error(msg)
             if current_len == 0:
                 raise ValueError(msg)

        return source_text

    def _sanitize_instruction(self, instruction: str) -> str:
        """
        Sanitize user instruction to prevent injection or formatting issues.
        Enforces strict content validation using shared validation logic.
        """
        try:
            return sanitize_instruction(instruction, self.config.max_instruction_length)
        except ValueError as e:
            logger.warning(f"Instruction rejected: {e}")
            msg = "Instruction contains forbidden content."
            raise ValueError(msg) from e

    def _generate_refinement_summary(self, source_text: str, instruction: str, node: SummaryNode) -> str:
        """Generate the new summary using the LLM."""
        if self.summarizer is None:
            msg = "Summarizer not initialized"
            raise RuntimeError(msg)

        level_key = node.metadata.dikw_level.value
        base_strategy_cls = STRATEGY_REGISTRY.get(level_key)
        base_strategy = base_strategy_cls() if base_strategy_cls else None
        strategy = RefinementStrategy(base_strategy=base_strategy)

        return self.summarizer.summarize(
            source_text,
            strategy=strategy,
            context={"instruction": instruction},
        )

    def _update_refined_node(self, node: SummaryNode, new_text: str, instruction: str) -> None:
        """Update the node in the store atomically."""
        node.text = new_text
        node.metadata.is_user_edited = True
        node.metadata.refinement_history.append(instruction)
        node.embedding = None

        try:
            self.store.update_node(node)
        except (StoreError, ValueError):
            logger.exception(f"Failed to persist refined node {node.id}")
            raise

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Refine a specific node based on user instruction.
        """
        validate_node_id(node_id)
        try:
            return self._refine_node_internal(node_id, instruction)
        except (ValueError, StoreError, RuntimeError) as e:
            logger.exception(f"Refinement failed for node {node_id}")
            msg = f"Refinement failed: {e}"
            raise RefinementError(msg) from e
        except Exception as e:
            logger.exception(f"Unexpected error during refinement for node {node_id}")
            msg = f"Unexpected error: {e}"
            raise RefinementError(msg) from e

    def _refine_node_internal(self, node_id: str, instruction: str) -> SummaryNode:
        """Internal logic for refinement."""
        node = self._validate_refinement_input(node_id, instruction)
        clean_instruction = self._sanitize_instruction(instruction)

        max_history = self.config.max_refinement_history
        if len(node.metadata.refinement_history) >= max_history:
             node.metadata.refinement_history.pop(0)

        source_text = self._retrieve_and_validate_children_content(node)

        if len(source_text) > self.config.max_input_length:
             logger.warning(f"Refinement source text for node {node_id} truncated.")
             source_text = source_text[:self.config.max_input_length]

        new_text = self._generate_refinement_summary(source_text, clean_instruction, node)

        # Sanitize output text to prevent injection of malicious content from LLM
        if len(new_text) > self.config.max_input_length:
             logger.warning(f"Refinement result for node {node_id} truncated.")
             new_text = new_text[:self.config.max_input_length]

        # Ensure no invalid control characters in the generated text
        try:
            from matome.utils.validation import check_control_chars
            check_control_chars(new_text, self.config.max_input_length)
        except ValueError as e:
            logger.warning(f"Refinement result for node {node_id} contains invalid chars: {e}")
            # We might choose to strip them or fail. For now, let's fail to be safe/strict as per Constitution.
            msg = f"Refinement result invalid: {e}"
            raise RefinementError(msg) from e

        self._update_refined_node(node, new_text, clean_instruction)

        logger.info(f"Refined node {node_id} with instruction: {clean_instruction}")
        return node
