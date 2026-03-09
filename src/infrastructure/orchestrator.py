import logging

from src.domain_models import (
    AIServiceError,
    AIServiceProtocol,
    ClusteringServiceProtocol,
    DocumentFactory,
    DocumentRepository,
    EntityExtractorProtocol,
    PipelineContext,
    TextSplitterProtocol,
)

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Handles the heavy lifting of orchestrating document ingestion and AI operations."""

    def __init__(
        self,
        doc_repo: DocumentRepository,
        ai_service: AIServiceProtocol,
        doc_factory: DocumentFactory,
        text_splitter: TextSplitterProtocol,
        entity_extractor: EntityExtractorProtocol,
        clustering_service: ClusteringServiceProtocol,
        pipeline_timeout: float,
        raptor_max_clusters: int,
    ) -> None:
        self.doc_repo = doc_repo
        self.ai_service = ai_service
        self.doc_factory = doc_factory
        self.text_splitter = text_splitter
        self.entity_extractor = entity_extractor
        self.clustering_service = clustering_service
        self.pipeline_timeout = pipeline_timeout
        self.raptor_max_clusters = raptor_max_clusters

    def _validate_content_length(self, content: str) -> None:
        if len(content) > self.doc_factory.max_content_length:
            msg = f"Root document content exceeds allowed length of {self.doc_factory.max_content_length} characters."
            raise ValueError(msg)

    def run_pipeline(self, context: PipelineContext) -> None:
        import multiprocessing

        logger.info("Starting document ingestion and analysis pipeline...")

        # We use a proper multiprocessing Process to ensure CPU bound tasks
        # like clustering or embedding don't permanently block threads
        # and can be reliably terminated on timeout.

        def process_target(ctx: PipelineContext) -> None:
            self._execute_pipeline_logic(ctx)

        process = multiprocessing.Process(target=process_target, args=(context,))
        process.start()
        process.join(self.pipeline_timeout)

        if process.is_alive():
            logger.error(f"Pipeline execution timed out after {self.pipeline_timeout} seconds. Terminating process.")
            process.terminate()
            process.join()
            msg = f"Pipeline execution timed out after {self.pipeline_timeout} seconds."
            raise TimeoutError(msg)

        if process.exitcode != 0:
            msg = f"Pipeline failed with exit code {process.exitcode}"
            raise RuntimeError(msg)

    def _get_chunks_and_content(self, context: PipelineContext) -> tuple[list[str], str]:
        if context.file_path:
            chunks = self.text_splitter.split_document(context.file_path)
            # Combine a truncated portion for summarization purposes to avoid blowing up the API
            # or use a dedicated map-reduce flow. For now, limit the summary context to first N chunks.
            combined_content = "\n".join(chunks[:5])
            return chunks, combined_content
        if context.content:
            return self.text_splitter.split_text(context.content), context.content

        msg = "PipelineContext must provide either content or file_path"
        raise ValueError(msg)

    def _execute_pipeline_logic(self, context: PipelineContext) -> None:
        # Initialize the transaction layer natively ensuring atomicity.
        self.doc_repo.begin()

        try:
            # 1. Ingestion and Semantic Chunking Stage
            logger.info("Ingesting document and performing semantic chunking...")
            chunks, combined_content = self._get_chunks_and_content(context)

            # 2. Entity Extraction Stage
            logger.info("Extracting entities...")
            entities = self.entity_extractor.extract_entities(chunks)

            # 3. RAPTOR Clustering and Tree Generation
            logger.info("Generating hierarchical tree via RAPTOR...")
            tree_metadata = self.clustering_service.cluster_chunks(chunks, self.raptor_max_clusters)

            # 4. Chain of Density (CoD) Summarization
            logger.info("Applying Chain of Density summarization...")
            self._validate_content_length(combined_content)
            try:
                summary = self.ai_service.generate_summary(combined_content)
            except AIServiceError as e:
                logger.warning(f"Summarization failed: {e}. Using fallback summary.")
                summary = "Fallback Summary: Content processing currently impaired due to AI unavailability."

            root_node = self.doc_factory.create_root_node(
                node_id=context.root_doc_id,
                title="Business Manual",
                content_text=combined_content,
                summary=summary,
            )

            # Update AI Processing metadata with extracted data
            root_node.metadata_container.ai_metadata.entity_metadata = entities
            root_node.metadata_container.ai_metadata.hierarchical_tree = tree_metadata
            root_node.metadata_container.ai_metadata.chunk_id = f"chunk_{context.root_doc_id}"
            root_node.metadata_container.ai_metadata.chunk_index = 0

            self.doc_repo.save_node(root_node)

            # 5. Question Generation
            logger.info(f"Generating learning loop for node {root_node.id}...")
            try:
                question = self.ai_service.generate_question(root_node)
                logger.info(f"AI Question: {question}")
            except AIServiceError as e:
                logger.warning(
                    f"Question generation failed: {e}. Skipping interactive prompt loop."
                )

            self.doc_repo.commit()
            logger.info("Pipeline execution completed successfully.")

        except Exception as e:
            logger.exception("Pipeline execution failed at an intermediate step. Rolling back...")
            self.doc_repo.rollback()
            msg = f"Pipeline failure: {e}"
            raise RuntimeError(msg) from e
