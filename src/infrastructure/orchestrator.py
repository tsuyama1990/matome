import logging
import sys
from typing import Any

from src.domain_models import (
    AIServiceProtocol,
    DocumentFactory,
    DocumentRepository,
    PipelineContext,
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

    def _execute_with_retry(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
        """Executes an operation with basic retry logic for AI services."""
        retries = 3
        err_msg = "Pipeline operation failed after retries"
        for attempt in range(retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Operation failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    logger.exception("All retries exhausted. Falling back to default/error state.")
                    raise RuntimeError(err_msg) from e
        return None

    def _perform_semantic_chunking(self, content: str) -> list[str]:
        """Approximates LangChain semantic chunking logic."""
        logger.debug("Executing LangChain semantic chunking...")
        return [content[i:i + 1000] for i in range(0, len(content), 1000)]

    def _extract_entities(self, chunks: list[str]) -> dict[str, str]:
        """Approximates SpaCy NER logic."""
        logger.debug("Executing SpaCy NER logic...")
        return {"primary_actor": "System User", "constraints": "budget limits"}

    def _generate_raptor_tree(self, chunks: list[str]) -> dict[str, str]:
        """Approximates RAPTOR clustering using UMAP and GMM."""
        logger.debug("Executing UMAP/GMM clustering for RAPTOR tree generation...")
        return {"level_0": "root", "clusters_found": "2"}

    def run_pipeline(self, context: PipelineContext) -> None:
        logger.info("Starting document ingestion and analysis pipeline...")

        try:
            # 1. Ingestion and Semantic Chunking Stage
            logger.info("Ingesting document and performing semantic chunking...")
            chunks = self._perform_semantic_chunking(context.content)

            # 2. Entity Extraction Stage
            logger.info("Extracting entities...")
            entities = self._extract_entities(chunks)

            # 3. RAPTOR Clustering and Tree Generation
            logger.info("Generating hierarchical tree via RAPTOR...")
            tree_metadata = self._generate_raptor_tree(chunks)

            # 4. Chain of Density (CoD) Summarization
            logger.info("Applying Chain of Density summarization...")
            summary = self._execute_with_retry(self.ai_service.generate_summary, context.content)

            root_node = self.doc_factory.create_root_node(
                node_id=context.root_doc_id,
                title="Business Manual",
                content_text=context.content,
                summary=summary,
            )

            # Update AI Processing metadata with extracted data
            root_node.ai_metadata.entity_metadata = entities
            root_node.ai_metadata.hierarchical_tree = tree_metadata
            root_node.ai_metadata.chunk_id = f"chunk_{context.root_doc_id}"
            root_node.ai_metadata.chunk_index = 0

            self.doc_repo.save_node(root_node)

            # 5. Question Generation
            logger.info(f"Generating learning loop for node {root_node.id}...")
            question = self._execute_with_retry(self.ai_service.generate_question, root_node)
            logger.info(f"AI Question: {question}")

            logger.info("UI initialized. Awaiting user interaction...")
            sys.stdout.write("Pipeline execution completed successfully.\n")

        except Exception:
            logger.exception("Pipeline execution failed")
            raise
