import logging
import threading

from src.config import Settings
from src.domain_models import (
    AIServiceProtocol,
    ClusteringServiceProtocol,
    DocumentFactory,
    DocumentRepository,
    EntityExtractorProtocol,
    PipelineContext,
    TextSplitterProtocol,
)
from src.infrastructure.services import (
    DefaultClusteringService,
    DefaultEntityExtractor,
    DefaultTextSplitter,
)

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Handles the heavy lifting of orchestrating document ingestion and AI operations."""

    def __init__(
        self,
        doc_repo: DocumentRepository,
        ai_service: AIServiceProtocol,
        doc_factory: DocumentFactory,
        settings: Settings | None = None,
        text_splitter: TextSplitterProtocol | None = None,
        entity_extractor: EntityExtractorProtocol | None = None,
        clustering_service: ClusteringServiceProtocol | None = None,
    ) -> None:
        self.doc_repo = doc_repo
        self.ai_service = ai_service
        self.doc_factory = doc_factory
        self.settings = settings or Settings()

        self.text_splitter = text_splitter or DefaultTextSplitter(
            chunk_size=self.settings.chunk_size, chunk_overlap=self.settings.chunk_overlap
        )
        self.entity_extractor = entity_extractor or DefaultEntityExtractor()
        self.clustering_service = clustering_service or DefaultClusteringService()

    def run_pipeline(self, context: PipelineContext) -> None:
        logger.info("Starting document ingestion and analysis pipeline...")

        def timeout_handler() -> None:
            msg = "Pipeline execution timed out."
            raise TimeoutError(msg)

        # Ensure pipeline doesn't hang indefinitely using a basic thread timeout implementation for blocking ML tasks
        timer = threading.Timer(self.settings.pipeline_timeout, timeout_handler)
        timer.start()

        # Initialize the transaction layer natively ensuring atomicity.
        self.doc_repo.begin()

        try:
            # 1. Ingestion and Semantic Chunking Stage
            logger.info("Ingesting document and performing semantic chunking...")
            chunks = self.text_splitter.split_text(context.content)

            # 2. Entity Extraction Stage
            logger.info("Extracting entities...")
            entities = self.entity_extractor.extract_entities(chunks)

            # 3. RAPTOR Clustering and Tree Generation
            logger.info("Generating hierarchical tree via RAPTOR...")
            tree_metadata = self.clustering_service.cluster_chunks(
                chunks, self.settings.raptor_max_clusters
            )

            # 4. Chain of Density (CoD) Summarization
            logger.info("Applying Chain of Density summarization...")
            summary = self.ai_service.generate_summary(context.content)

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
            question = self.ai_service.generate_question(root_node)
            logger.info(f"AI Question: {question}")

            self.doc_repo.commit()
            logger.info("Pipeline execution completed successfully.")

        except Exception as e:
            logger.exception("Pipeline execution failed at an intermediate step. Rolling back...")
            self.doc_repo.rollback()
            msg = f"Pipeline failure: {e}"
            raise RuntimeError(msg) from e
        finally:
            timer.cancel()
