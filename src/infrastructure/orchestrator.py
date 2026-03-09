import logging
import sys

from src.domain_models import (
    AIServiceProtocol,
    DocumentFactory,
    DocumentRepository,
)

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Handles the heavy lifting of orchestrating document ingestion and AI operations."""

    def __init__(
        self,
        doc_repo: DocumentRepository,
        ai_service: AIServiceProtocol,
        doc_factory: DocumentFactory,
    ) -> None:
        self.doc_repo = doc_repo
        self.ai_service = ai_service
        self.doc_factory = doc_factory

    def run_pipeline(self, root_doc_id: str, content: str) -> None:
        logger.info("Starting document ingestion and analysis pipeline...")

        # 1. Ingestion Stage
        logger.info("Ingesting document...")

        summary = self.ai_service.generate_summary(content)

        root_node = self.doc_factory.create_root_node(
            node_id=root_doc_id, title="Business Manual", content_text=content, summary=summary
        )
        self.doc_repo.save_node(root_node)

        # 2. AI Processing Stage (Mocked)
        logger.info(f"Generating learning loop for node {root_node.id}...")
        question = self.ai_service.generate_question(root_node)
        logger.info(f"AI Question: {question}")

        # 3. UI Initialization placeholder
        logger.info("UI initialized. Awaiting user interaction...")

        sys.stdout.write("Pipeline execution completed successfully.\n")
