import logging
import re
from collections import deque
from collections.abc import Iterator

from domain_models.config import ProcessingConfig
from domain_models.constants import PROMPT_INJECTION_PATTERNS
from domain_models.manifest import Chunk, SummaryNode
from domain_models.types import NodeID
from matome.agents.strategies import (
    STRATEGY_REGISTRY,
    RefinementStrategy,
)
from matome.agents.summarizer import SummarizationAgent
from matome.exceptions import MatomeError
from matome.utils.store import DiskChunkStore, StoreError

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

        yield from self._traverse_source_chunks(node, limit)

    def _traverse_source_chunks(self, root: SummaryNode, limit: int | None) -> Iterator[Chunk]:
        """
        Helper to traverse source chunks using layer-by-layer BFS with batch fetching.
        Reduces N+1 queries by fetching children of the entire current layer at once.
        """
        queue: deque[SummaryNode] = deque([root])
        visited: set[str] = {str(root.id)}
        yielded_count = 0

        # Max queue size safety
        MAX_QUEUE_SIZE = 10000

        while queue:
            if limit and yielded_count >= limit:
                break

            # Process current layer
            current_layer_nodes = list(queue)
            queue.clear()

            # Collect all child IDs for this layer
            all_child_ids: list[str | int] = []
            for node in current_layer_nodes:
                all_child_ids.extend(node.children_indices)

            if not all_child_ids:
                continue

            try:
                # Batch fetch all children for this layer
                for child in self.store.get_nodes(all_child_ids):
                    if child is None:
                        continue

                    if isinstance(child, Chunk):
                        yield child
                        yielded_count += 1
                        if limit and yielded_count >= limit:
                            break
                    # child is SummaryNode because get_nodes return type union, checked Chunk above
                    elif str(child.id) not in visited:
                        visited.add(str(child.id))
                        if len(queue) < MAX_QUEUE_SIZE:
                            queue.append(child) # type: ignore[arg-type]
                        else:
                            logger.warning("Traversal queue limit reached. Truncating search.")
            except (StoreError, ValueError):
                logger.exception("Error during source chunk traversal")
                break

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

    def _retrieve_children_content(self, node: SummaryNode) -> tuple[list[str], int]:
        """
        Stream children and collect text.
        Returns: (list of text chunks, total length)
        """
        limit = self.config.max_input_length * self.config.refinement_context_limit_multiplier
        current_len = 0
        child_texts: list[str] = []

        try:
            for child in self.get_children(node):
                text_len = len(child.text)
                if current_len + text_len > limit:
                    logger.warning(
                        f"Refinement source text for node {node.id} exceeds safety limit ({limit}). Truncating."
                    )
                    break
                child_texts.append(child.text)
                current_len += text_len
        except (StoreError, ValueError):
            logger.exception(f"Error retrieving children content for node {node.id}")
            raise

        return child_texts, current_len

    def _retrieve_and_validate_children_content(self, node: SummaryNode) -> str:
        """
        Retrieve children, validate count, and concatenate content safely.
        Returns the concatenated source text.
        """
        child_texts, current_len = self._retrieve_children_content(node)
        children_count = len(child_texts)

        if children_count == 0:
             msg = f"Node {node.id} has no accessible children. Cannot refine."
             raise ValueError(msg)

        limit = self.config.max_input_length * self.config.refinement_context_limit_multiplier
        if children_count != len(node.children_indices) and current_len <= limit:
             msg = f"Node {node.id} expects {len(node.children_indices)} children but found {children_count}."
             logger.error(msg)
             if current_len == 0:
                 raise ValueError(msg)

        return "\n\n".join(child_texts)

    def _sanitize_instruction(self, instruction: str) -> str:
        """
        Sanitize user instruction to prevent injection or formatting issues.
        Enforces strict content validation.
        """
        clean = instruction.strip()

        if len(clean) > self.config.max_instruction_length:
             clean = clean[:self.config.max_instruction_length]

        # Check for injection patterns
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, clean):
                msg = f"Instruction contains forbidden pattern: {pattern}"
                logger.warning(msg)
                error_msg = "Instruction contains forbidden content."
                raise ValueError(error_msg)

        # Basic sanitization
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', clean)

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
        try:
            return self._refine_node_internal(node_id, instruction)
        except Exception:
            logger.exception(f"Refinement failed for node {node_id}")
            raise

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

        self._update_refined_node(node, new_text, clean_instruction)

        logger.info(f"Refined node {node_id} with instruction: {clean_instruction}")
        return node
