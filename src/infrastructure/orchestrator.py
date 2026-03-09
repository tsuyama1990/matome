import logging
import typing
from typing import Any

from src.domain_models import (
    AIServiceError,
    AIServiceProtocol,
    ClusteringServiceProtocol,
    DocumentFactory,
    DocumentNode,
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

        queue: multiprocessing.Queue[Any] = multiprocessing.Queue()

        def process_target(ctx: PipelineContext, q: Any) -> None:
            try:
                result = self._execute_pipeline_logic(ctx)
                q.put(result)
            except Exception as e:
                q.put(e)

        process = multiprocessing.Process(target=process_target, args=(context, queue))
        try:
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

            result = queue.get()
            if isinstance(result, Exception):
                raise result

            if result is not None:
                self.doc_repo.save_node(result)
                self.doc_repo.commit()
        finally:
            if process.is_alive():
                process.terminate()
                process.join()
            process.close()

    def _get_chunk_iterator_and_content(self, context: PipelineContext) -> tuple[typing.Iterator[str], str]:
        import itertools
        if context.file_path:
            # We tee the generator into two iterators to avoid exhausting the single stream,
            # allowing sequential stream consumption without forced list materialization.
            # Warning: tee buffers elements if consumers advance at different speeds.
            # Since we consume them sequentially, we should process them iteratively,
            # but to fully avoid buffering, the best is to just re-open the stream or use MiniBatch processing.
            # We will use re-yielding to avoid loading full streams at once.

            # Extract truncated content for summarizer limit bounds
            preview_chunks = list(itertools.islice(self.text_splitter.split_document(context.file_path), 5))
            combined_content = "\n".join(preview_chunks)

            return self.text_splitter.split_document(context.file_path), combined_content
        if context.content:
            return iter(self.text_splitter.split_text(context.content)), context.content

        msg = "PipelineContext must provide either content or file_path"
        raise ValueError(msg)

    def _execute_pipeline_logic(self, context: PipelineContext) -> DocumentNode:
        try:
            # 1. Ingestion and Semantic Chunking Stage
            logger.info("Ingesting document and performing semantic chunking...")
            chunks_iterator, combined_content = self._get_chunk_iterator_and_content(context)

            # 2. Entity Extraction Stage
            logger.info("Extracting entities via streaming...")
            entities = self.entity_extractor.extract_entities(chunks_iterator)

            # 3. RAPTOR Clustering and Tree Generation
            # Regenerate the iterator to stream to the clustering service safely
            # without expanding everything to a list.
            logger.info("Generating hierarchical tree via RAPTOR streaming...")
            if context.file_path:
                clustering_iterator = self.text_splitter.split_document(context.file_path)
            else:
                clustering_iterator = iter(self.text_splitter.split_text(context.content)) # type: ignore

            tree_metadata = self.clustering_service.cluster_chunks(clustering_iterator, self.raptor_max_clusters)

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

            # 5. Question Generation
            logger.info(f"Generating learning loop for node {root_node.id}...")
            try:
                question = self.ai_service.generate_question(root_node)
                logger.info(f"AI Question: {question}")
            except AIServiceError as e:
                logger.warning(
                    f"Question generation failed: {e}. Skipping interactive prompt loop."
                )

        except Exception as e:
            logger.exception("Pipeline execution failed at an intermediate step.")
            msg = f"Pipeline failure: {e}"
            raise RuntimeError(msg) from e
        else:
            logger.info("Pipeline ML logic completed successfully.")
            return root_node
