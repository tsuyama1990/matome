import logging
from typing import Any

from domain_models.config import ProcessingConfig
from domain_models.manifest import SummaryNode
from domain_models.types import NodeID
from matome.agents.strategies import RefinementStrategy
from matome.engines.embedder import EmbeddingService
from matome.interfaces import Summarizer
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


class InteractiveRaptorEngine:
    """
    Engine for interactive refinement of the RAPTOR tree.
    Allows for single-node updates based on user instructions.

    This engine is designed to support the "Interactive Refinement" feature (Cycle 03),
    where users can manually tweak specific summary nodes in the tree.
    It handles:
    1. Fetching the target node from the persistent store.
    2. Invoking the LLM with a `RefinementStrategy` to rewrite the content.
    3. Re-embedding the new content to keep the vector space consistent.
    4. Updating the node's metadata (history, edited flag) and persisting it.
    """

    def __init__(
        self,
        summarizer: Summarizer,
        embedder: EmbeddingService,
        config: ProcessingConfig,
    ) -> None:
        """
        Initialize the InteractiveRaptorEngine.

        Args:
            summarizer: The summarization agent responsible for text generation.
            embedder: Service for re-embedding nodes after modification.
            config: Processing configuration containing model settings.
        """
        self.summarizer = summarizer
        self.embedder = embedder
        self.config = config

    def refine_node(
        self, node_id: NodeID, instruction: str, store: DiskChunkStore
    ) -> SummaryNode:
        """
        Refine a specific node based on user instructions.

        This process is transactional in nature:
        - The node is locked (conceptually) during update.
        - The embedding is updated synchronously to ensure the node is retrieval-ready.
        - Metadata is updated to track provenance.

        Args:
            node_id: The ID of the node to refine.
            instruction: The user's refinement instruction (e.g., "Make it shorter").
            store: The persistent store containing the node.

        Returns:
            The updated SummaryNode.

        Raises:
            ValueError: If the node is not found in the store.
            TypeError: If the target node is a raw Chunk (Level 0), which cannot be refined.
            RuntimeError: If embedding generation fails.
        """
        logger.debug(f"Attempting to refine node {node_id}...")

        # 1. Fetch Node
        node = store.get_node(node_id)
        if not node:
            msg = f"Node {node_id} not found."
            logger.error(msg)
            raise ValueError(msg)

        if not isinstance(node, SummaryNode):
            msg = "Cannot refine raw data chunks. Only summary nodes can be refined."
            logger.error(msg)
            raise TypeError(msg)

        logger.debug(f"Node {node_id} fetched. Current text length: {len(node.text)}")

        # 2. Refine using LLM
        # We use RefinementStrategy
        strategy = RefinementStrategy()
        context: dict[str, Any] = {"instruction": instruction}

        logger.info(f"Refining node {node_id} with instruction: '{instruction}'")

        # Original text is passed as input
        new_text = self.summarizer.summarize(
            text=node.text,
            config=self.config,
            strategy=strategy,
            context=context,
        )
        logger.debug(f"LLM refinement complete. New text length: {len(new_text)}")

        # 3. Update Node Metadata
        node.text = new_text
        node.metadata.is_user_edited = True
        node.metadata.refinement_history.append(instruction)

        # 4. Re-embed
        logger.debug(f"Re-embedding node {node_id}...")
        try:
            # embed_strings returns an iterator, we take the first item
            embeddings = list(self.embedder.embed_strings([new_text]))
            if embeddings:
                node.embedding = embeddings[0]
            else:
                 # Should not happen if embedder works correctly
                msg = "Embedder returned no embeddings."
                raise RuntimeError(msg)  # noqa: TRY301
        except Exception:
            logger.exception(f"Failed to re-embed refined node {node_id}")
            # Raise error to ensure consistency
            raise

        # 5. Save to Store
        # We use add_summary which uses "OR REPLACE" logic in store
        logger.debug(f"Persisting updated node {node_id} to store...")
        store.add_summary(node)

        logger.info(f"Node {node_id} refined, re-embedded, and saved successfully.")
        return node
