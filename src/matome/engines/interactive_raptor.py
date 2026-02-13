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
    Interactive engine for manipulating the RAPTOR tree.
    Allows for single-node refinement and traversal.
    """

    def __init__(self, store: DiskChunkStore, agent: SummarizationAgent) -> None:
        """
        Initialize the interactive engine.

        Args:
            store: The disk-based store containing chunks and summary nodes.
                   Provides persistent storage access.
            agent: The summarization agent to use for refinement.
                   Handles LLM interactions.
        """
        self.store = store
        self.agent = agent

    def get_node(self, node_id: str | int) -> SummaryNode | Chunk | None:
        """
        Get a node from the store by ID.

        Args:
            node_id: The ID of the node (int for Chunk, str for SummaryNode).

        Returns:
            The node object if found, otherwise None.
        """
        return self.store.get_node(node_id)

    def get_children(self, node_id: str) -> list[SummaryNode | Chunk]:
        """
        Get children of a specific summary node.

        Args:
            node_id: The ID of the parent summary node.

        Returns:
            A list of child nodes (SummaryNode or Chunk).
            Returns an empty list if the parent node is not found or is a Chunk.
        """
        node = self.get_node(node_id)
        if not node or not isinstance(node, SummaryNode):
            return []

        children = []
        for child_id in node.children_indices:
            child = self.store.get_node(child_id)
            if child:
                children.append(child)
        return children

    def _get_refinement_strategy(self, current_level: DIKWLevel) -> RefinementStrategy:
        """
        Helper to determine the base strategy and wrap it in RefinementStrategy.

        This method maps the DIKW level of a node to its corresponding PromptStrategy.
        - Wisdom -> WisdomStrategy
        - Knowledge -> KnowledgeStrategy
        - Information -> InformationStrategy
        - Data/Other -> BaseSummaryStrategy

        The resulting strategy is then wrapped in RefinementStrategy to allow for
        user instruction injection.
        """
        base_strategy: PromptStrategy

        if current_level == DIKWLevel.WISDOM:
            base_strategy = WisdomStrategy()
        elif current_level == DIKWLevel.KNOWLEDGE:
            base_strategy = KnowledgeStrategy()
        elif current_level == DIKWLevel.INFORMATION:
            base_strategy = InformationStrategy()
        else:
            # Fallback for DATA or unknown levels
            if current_level != DIKWLevel.DATA:
                logger.warning(
                    f"Unknown or unexpected DIKW level '{current_level}'. Falling back to BaseSummaryStrategy."
                )
            base_strategy = BaseSummaryStrategy()

        return RefinementStrategy(base_strategy)

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Refine a summary node with a user instruction.

        Re-summarizes the node's children using the appropriate strategy (based on DIKW level)
        and the provided user instruction. The updated node is saved back to the store.

        Args:
            node_id: The ID of the node to refine.
            instruction: The user's refinement instruction (e.g., "Make it simpler").

        Returns:
            The newly generated SummaryNode.

        Raises:
            ValueError: If the node with `node_id` is not found, `instruction` is empty, or `model_dump()` fails.
            TypeError: If the node is a Chunk (cannot be refined).
        """
        if not instruction or not instruction.strip():
            msg = "Refinement instruction cannot be empty."
            logger.error(msg)
            raise ValueError(msg)

        node = self.get_node(node_id)
        if not node:
            msg = f"Node {node_id} not found."
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = f"Cannot refine a Chunk (Node ID: {node_id}). Only SummaryNodes can be refined."
            raise TypeError(msg)

        strategy = self._get_refinement_strategy(node.metadata.dikw_level)

        # Gather children text
        children_texts = []
        for child_id in node.children_indices:
            child = self.store.get_node(child_id)
            if child:
                children_texts.append(child.text)

        if not children_texts:
            logger.warning(
                f"Node {node_id} has no accessible children. Refining using the node's own text as context."
            )
            children_texts = [node.text]

        # Prepare context for summarization
        try:
            # We start with existing metadata but must convert to dict for context
            meta_dict = node.metadata.model_dump()
        except Exception as e:
            msg = f"Failed to dump metadata for node {node_id}: {e}"
            logger.exception(msg)
            raise ValueError(msg) from e

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
            "instruction": instruction,
        }

        # Summarize
        new_node = self.agent.summarize(children_texts, context=context, strategy=strategy)

        # Update store with the new node content
        # Note: This overwrites the existing node in the store because IDs match.
        self.store.add_summary(new_node)

        logger.info(f"Successfully refined node {node_id} with instruction: '{instruction}'")
        return new_node
