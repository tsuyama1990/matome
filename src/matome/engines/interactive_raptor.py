import logging

from domain_models.data_schema import DIKWLevel
from domain_models.manifest import Chunk, SummaryNode
from matome.agents.strategies import (
    BaseSummaryStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    RefinementStrategy,
    WisdomStrategy,
)
from matome.agents.summarizer import SummarizationAgent
from matome.interfaces import PromptStrategy
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


class InteractiveRaptorEngine:
    """
    Engine for interactive operations on the knowledge graph.
    Supports single-node retrieval and refinement.
    """

    def __init__(self, store: DiskChunkStore, agent: SummarizationAgent) -> None:
        """
        Initialize the interactive engine.

        Args:
            store: The persistence layer (DiskChunkStore).
            agent: The summarization agent to use for refinement.
        """
        self.store = store
        self.agent = agent

    def get_node(self, node_id: str) -> SummaryNode | Chunk | None:
        """
        Retrieve a node from the store.

        Args:
            node_id: The unique ID of the node.

        Returns:
            The node object (Chunk or SummaryNode) or None if not found.
        """
        return self.store.get_node(node_id)

    def get_nodes_by_level(self, level: str) -> list[SummaryNode]:
        """
        Retrieve all summary nodes at a specific DIKW level.

        Args:
            level: The DIKW level (e.g., 'wisdom', 'knowledge').

        Returns:
            List of SummaryNodes.
        """
        return self.store.get_nodes_by_level(level)

    def get_children(self, node_id: str) -> list[SummaryNode | Chunk]:
        """
        Retrieve the immediate children of a node.

        Args:
            node_id: The ID of the parent node.

        Returns:
            List of child nodes (SummaryNode or Chunk).
        """
        node = self.store.get_node(node_id)
        if not node or not isinstance(node, SummaryNode):
            return []

        # children_indices is list[int | str]
        # We rely on get_nodes to handle the batch retrieval efficiently
        children_map = self.store.get_nodes(node.children_indices)

        # Filter out None values and return list
        # Note: The order of children_indices matters for reading, so we iterate through indices
        children = []
        for child_id in node.children_indices:
            child = children_map.get(child_id)
            if child:
                children.append(child)
        return children

    def get_source_chunks(self, node_id: str) -> list[Chunk]:
        """
        Recursively retrieve all leaf chunks (DATA level) for a given node.
        Uses iterative DFS with batch pre-fetching to optimize SQLite access.

        Args:
            node_id: The ID of the root node to traverse from.

        Returns:
            List of Chunk objects in reading order (DFS).
        """
        root = self.store.get_node(node_id)
        if not root:
            return []

        if isinstance(root, Chunk):
            return [root]

        # Stack contains IDs to process
        # We start with the children of the root
        stack: list[str | int] = list(root.children_indices)
        stack.reverse()  # Reverse so we pop the first child first (DFS)

        chunks: list[Chunk] = []

        # Local cache to avoid repeated DB calls and support batch fetching
        node_cache: dict[str | int, SummaryNode | Chunk] = {}

        while stack:
            # Optimization: identify which nodes in the *top* of the stack are missing from cache
            # We can't peek deep into stack easily, but we can peek the top batch.
            BATCH_SIZE = 50

            # IDs we need to process soon (from the end of the list/stack)
            upcoming_ids = stack[-BATCH_SIZE:]
            missing_ids = [nid for nid in upcoming_ids if nid not in node_cache]

            if missing_ids:
                fetched = self.store.get_nodes(missing_ids)
                # Filter None and update cache
                for nid, node in fetched.items():
                    if node:
                        node_cache[nid] = node

            # Now proceed with DFS
            current_id = stack.pop()

            node = node_cache.get(current_id)
            if not node:
                # If not in cache (maybe fetch failed or missing in DB), try direct fetch
                # This is a fallback
                node = self.store.get_node(current_id)

            if not node:
                continue

            # Clean up cache to save memory (we visit each node once in a tree)
            # Use pop to remove if present
            if current_id in node_cache:
                del node_cache[current_id]

            if isinstance(node, Chunk):
                chunks.append(node)
            elif isinstance(node, SummaryNode):
                # Push children to stack
                children = list(node.children_indices)
                children.reverse()
                stack.extend(children)

        return chunks

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Refine a node based on user instruction.

        Args:
            node_id: The ID of the node to refine.
            instruction: The user's refinement instruction.

        Returns:
            The updated SummaryNode.

        Raises:
            ValueError: If the node is not found.
            TypeError: If the node is not a SummaryNode.
        """
        node = self.store.get_node(node_id)
        if not node:
            msg = f"Node {node_id} not found."
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = "Cannot refine a raw Chunk. Only SummaryNodes can be refined."
            raise TypeError(msg)

        # Basic security validation for instruction
        if not instruction or len(instruction) > 1000:
            msg = "Instruction must be non-empty and less than 1000 characters."
            raise ValueError(msg)

        # Determine base strategy from DIKW level
        dikw_level = node.metadata.dikw_level
        base_strategy: PromptStrategy

        if dikw_level == DIKWLevel.WISDOM:
            base_strategy = WisdomStrategy()
        elif dikw_level == DIKWLevel.KNOWLEDGE:
            base_strategy = KnowledgeStrategy()
        elif dikw_level == DIKWLevel.INFORMATION:
            base_strategy = InformationStrategy()
        else:
            base_strategy = BaseSummaryStrategy()

        # Wrap with RefinementStrategy
        refinement_strategy = RefinementStrategy(base_strategy)

        # Prepare context
        context = {
            "id": node.id,
            "level": node.level,
            "children_indices": node.children_indices,
            "instruction": instruction,
            # Pass existing metadata to preserve fields like cluster_id
            "metadata": node.metadata.model_dump(),
        }

        # Call agent to generate new summary using the refinement strategy override
        # We pass the OLD text as input to be rewritten
        new_node = self.agent.summarize(
            text=node.text, context=context, strategy=refinement_strategy
        )

        # Update metadata
        new_node.metadata.is_user_edited = True
        new_node.metadata.refinement_history = [*node.metadata.refinement_history, instruction]

        # Preserve original DIKW level if agent didn't set it (though strategies usually do)
        if new_node.metadata.dikw_level == DIKWLevel.DATA and dikw_level != DIKWLevel.DATA:
            new_node.metadata.dikw_level = dikw_level

        # Ensure we keep other metadata if not overwritten (e.g. cluster_id)
        if node.metadata.cluster_id and not new_node.metadata.cluster_id:
            new_node.metadata.cluster_id = node.metadata.cluster_id

        if node.metadata.type and not new_node.metadata.type:
            new_node.metadata.type = node.metadata.type

        # Save to store
        self.store.add_summary(new_node)

        return new_node
