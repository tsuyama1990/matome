import logging

from domain_models.data_schema import DIKWLevel
from domain_models.manifest import Chunk, SummaryNode
from matome.agents.summarizer import SummarizationAgent
from matome.strategies import (
    BaseSummaryStrategy,
    DefaultStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


class InteractiveRaptorEngine:
    """
    Interactive engine for manipulating the RAPTOR tree.
    Allows for single-node refinement and traversal.
    """

    def __init__(self, store: DiskChunkStore, agent: SummarizationAgent) -> None:
        self.store = store
        self.agent = agent

    def get_node(self, node_id: str | int) -> SummaryNode | Chunk | None:
        """Get a node from the store."""
        return self.store.get_node(node_id)

    def get_children(self, node_id: str) -> list[SummaryNode | Chunk]:
        """Get children of a specific node."""
        node = self.get_node(node_id)
        if not node or not isinstance(node, SummaryNode):
            return []

        children = []
        for child_id in node.children_indices:
            child = self.store.get_node(child_id)
            if child:
                children.append(child)
        return children

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Refine a node with user instruction.
        Re-summarizes the node's children using the appropriate strategy and the user's instruction.
        """
        node = self.get_node(node_id)
        if not node:
             msg = f"Node {node_id} not found."
             raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = f"Cannot refine a Chunk (Node ID: {node_id}). Only SummaryNodes can be refined."
            raise TypeError(msg)

        # Determine strategy based on current level
        current_level = node.metadata.dikw_level
        strategy: BaseSummaryStrategy

        if current_level == DIKWLevel.WISDOM:
            strategy = WisdomStrategy()
        elif current_level == DIKWLevel.KNOWLEDGE:
             strategy = KnowledgeStrategy()
        elif current_level == DIKWLevel.INFORMATION:
             strategy = InformationStrategy()
        else:
             strategy = DefaultStrategy()

        # Gather children text
        children_texts = []
        for child_id in node.children_indices:
            child = self.store.get_node(child_id)
            if child:
                children_texts.append(child.text)

        if not children_texts:
            logger.warning(f"Node {node_id} has no accessible children. Refining text itself.")
            children_texts = [node.text]

        # Prepare context for summarization
        # We start with existing metadata but must convert to dict for context
        meta_dict = node.metadata.model_dump()

        # Update metadata for refinement
        meta_dict["is_user_edited"] = True

        # Append instruction to history
        current_history = meta_dict.get("refinement_history", [])
        if not isinstance(current_history, list):
            current_history = []
        current_history.append(instruction)
        meta_dict["refinement_history"] = current_history

        context = {
            "id": node.id,
            "level": node.level,
            "children_indices": node.children_indices,
            "metadata": meta_dict,
            "instruction": instruction
        }

        # Summarize
        new_node = self.agent.summarize(children_texts, context=context, strategy=strategy)

        # Update store with the new node content
        # Note: This overwrites the existing node in the store because IDs match.
        self.store.add_summary(new_node)

        return new_node
