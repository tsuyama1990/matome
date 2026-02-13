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
