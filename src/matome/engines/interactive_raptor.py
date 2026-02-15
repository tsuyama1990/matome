import logging
import re
from collections import deque
from collections.abc import Iterator

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, SummaryNode
from domain_models.types import NodeID
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

    def get_node(self, node_id: NodeID) -> SummaryNode | Chunk | None:
        """
        Retrieve a node (Summary or Chunk) by its unique ID.
        Delegates to the underlying DiskChunkStore.
        """
        try:
            return self.store.get_node(node_id)
        except Exception:
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
        except Exception:
            logger.exception(f"Failed to retrieve node {node_id} for source tracing")
            return

        if not node:
            return

        if isinstance(node, Chunk):
            yield node
            return

        yield from self._traverse_source_chunks(node, limit)

    def _traverse_source_chunks(self, root: SummaryNode, limit: int | None) -> Iterator[Chunk]:
        """Helper to traverse source chunks using BFS."""
        # BFS Traversal using deque for O(1) pops
        queue: deque[SummaryNode] = deque([root])
        visited: set[str] = {str(root.id)}
        yielded_count = 0

        while queue:
            if limit and yielded_count >= limit:
                break

            try:
                current = queue.popleft()
                child_ids = current.children_indices

                # Fetch children in batch
                for child in self.store.get_nodes(child_ids):
                    if child is None:
                        continue

                    if isinstance(child, Chunk):
                        yield child
                        yielded_count += 1
                        if limit and yielded_count >= limit:
                            break
                    elif isinstance(child, SummaryNode) and str(child.id) not in visited:
                        visited.add(str(child.id))
                        queue.append(child)
            except Exception:
                logger.exception("Error during source chunk traversal")
                break

    def get_children(self, node: SummaryNode) -> Iterator[SummaryNode | Chunk]:
        """
        Retrieve the immediate children of a given summary node.
        Returns an iterator to support streaming processing.

        Returns:
            Iterator[SummaryNode | Chunk]: The immediate children of the given node.
        """
        # Batch retrieve children for efficiency (avoid N+1)
        child_ids = node.children_indices

        try:
            # get_nodes returns a generator and fetches in batches
            for child in self.store.get_nodes(child_ids):
                if child is not None:
                    yield child
        except Exception:
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
        except Exception:
            logger.exception("Failed to retrieve root node")
            raise

    def _get_root_node_internal(self) -> SummaryNode | None:
        """Internal helper for root node retrieval."""
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
        except Exception:
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

    def _retrieve_and_validate_children_content(self, node: SummaryNode) -> str:
        """
        Retrieve children, validate count, and concatenate content safely.
        Returns the concatenated source text.
        """
        limit = self.config.max_input_length * self.config.refinement_context_limit_multiplier
        current_len = 0
        children_count = 0
        child_texts: list[str] = []

        try:
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
        except Exception:
            logger.exception(f"Error retrieving children content for node {node.id}")
            raise

        if children_count == 0:
             msg = f"Node {node.id} has no accessible children. Cannot refine."
             raise ValueError(msg)

        # Basic consistency check
        if children_count != len(node.children_indices) and current_len <= limit:
             msg = f"Node {node.id} expects {len(node.children_indices)} children but found {children_count}."
             logger.error(msg)
             # We allow partial recovery if some children are missing but we found some content
             if current_len == 0:
                 raise ValueError(msg)

        return "\n\n".join(child_texts)

    def _sanitize_instruction(self, instruction: str) -> str:
        """
        Sanitize user instruction to prevent injection or formatting issues.
        Enforces strict content validation.
        """
        # Strip leading/trailing whitespace
        clean = instruction.strip()

        # Length check (redundant but safe)
        if len(clean) > self.config.max_instruction_length:
             clean = clean[:self.config.max_instruction_length]

        # Remove control characters (except newline/tab) which can mess up logging or some parsers
        # Using a regex to keep only printable characters + newline + tab
        # Also strictly disallow common injection patterns if any (though LLM is the sink)
        # We rely on SummarizationAgent's SYSTEM_INJECTION_PATTERNS for deep inspection,
        # but here we ensure basic string hygiene.

        # Remove ASCII control chars < 32 except 9 (tab), 10 (LF), 13 (CR)
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

        # update_node in DiskChunkStore is atomic (uses explicit transaction)
        try:
            self.store.update_node(node)
        except Exception:
            logger.exception(f"Failed to persist refined node {node.id}")
            raise

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Refine a specific node based on user instruction.

        Refactored to be cleaner and safer:
        1. Validate inputs
        2. Sanitize instruction
        3. Retrieve context
        4. Generate summary
        5. Update store
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

        # Enforce history limit
        max_history = self.config.max_refinement_history
        if len(node.metadata.refinement_history) >= max_history:
             # FIFO eviction
             node.metadata.refinement_history.pop(0)

        source_text = self._retrieve_and_validate_children_content(node)

        # Truncate source text if it exceeds limits to prevent context overflow errors
        if len(source_text) > self.config.max_input_length:
             logger.warning(f"Refinement source text for node {node_id} truncated to {self.config.max_input_length} chars.")
             source_text = source_text[:self.config.max_input_length]

        new_text = self._generate_refinement_summary(source_text, clean_instruction, node)

        self._update_refined_node(node, new_text, clean_instruction)

        logger.info(f"Refined node {node_id} with instruction: {clean_instruction}")
        return node
