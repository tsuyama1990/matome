import logging
import sys

from src.config import Settings
from src.domain_models import (
    AIProcessingMetadata,
    DocumentContent,
    DocumentNode,
    NodeMetadata,
    NodeStatus,
)
from src.interfaces.protocols import AIServiceProtocol, DocumentRepository

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Handles the heavy lifting of orchestrating document ingestion and AI operations."""

    def __init__(
        self, doc_repo: DocumentRepository, ai_service: AIServiceProtocol, settings: Settings
    ) -> None:
        self.doc_repo = doc_repo
        self.ai_service = ai_service
        self.settings = settings

    def run_pipeline(self) -> None:
        logger.info("Starting document ingestion and analysis pipeline...")

        # 1. Ingestion Stage
        content = self.settings.default_content
        logger.info("Ingesting document...")

        root_node = DocumentNode(
            id=self.settings.default_root_doc_id,
            parent_id=None,
            title="Business Manual",
            content=DocumentContent(
                summary=self.ai_service.generate_summary(content), text=content
            ),
            status=NodeStatus.LOCKED,
            metadata=NodeMetadata(
                category="business", author="System", source="upload", time_axis=None
            ),
            ai_metadata=AIProcessingMetadata(chunk_id=None, chunk_index=None),
        )
        self.doc_repo.save_node(root_node)

        # 2. AI Processing Stage (Mocked)
        logger.info(f"Generating learning loop for node {root_node.id}...")
        question = self.ai_service.generate_question(root_node)
        logger.info(f"AI Question: {question}")

        # 3. UI Initialization placeholder
        logger.info("UI initialized. Awaiting user interaction...")

        sys.stdout.write("Pipeline execution completed successfully.\n")
