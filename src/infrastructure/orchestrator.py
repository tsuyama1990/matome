import logging
import typing
from typing import Any

from src.domain_models import (
    AIServiceError,
    ClusteringServiceProtocol,
    DocumentFactory,
    DocumentNode,
    DocumentRepository,
    EntityExtractorProtocol,
    MetadataService,
    PipelineContext,
    QuestionServiceProtocol,
    SummaryServiceProtocol,
    TextSplitterProtocol,
    TransactionManager,
)

logger = logging.getLogger(__name__)


class PipelineConfig:
    """Encapsulates configuration settings for the pipeline."""

    def __init__(
        self,
        pipeline_timeout: float,
        raptor_max_clusters: int,
    ) -> None:
        self.pipeline_timeout = pipeline_timeout
        self.raptor_max_clusters = raptor_max_clusters


class PipelineDependencies:
    """Encapsulates dependencies required by the pipeline."""

    def __init__(
        self,
        doc_repo: DocumentRepository,
        transaction_manager: TransactionManager,
        summary_service: SummaryServiceProtocol,
        question_service: QuestionServiceProtocol,
        doc_factory: DocumentFactory,
        metadata_service: MetadataService,
        text_splitter: TextSplitterProtocol,
        entity_extractor: EntityExtractorProtocol,
        clustering_service: ClusteringServiceProtocol,
    ) -> None:
        self.doc_repo = doc_repo
        self.transaction_manager = transaction_manager
        self.summary_service = summary_service
        self.question_service = question_service
        self.doc_factory = doc_factory
        self.metadata_service = metadata_service
        self.text_splitter = text_splitter
        self.entity_extractor = entity_extractor
        self.clustering_service = clustering_service


class ProcessManager:
    """Handles multiprocessing process lifecycle management."""

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def run_with_timeout(
        self, target_func: typing.Callable[[PipelineContext], Any], context: PipelineContext
    ) -> Any:
        import multiprocessing

        queue: multiprocessing.Queue[Any] = multiprocessing.Queue()

        def process_target(ctx: PipelineContext, q: Any) -> None:
            try:
                result = target_func(ctx)
                q.put(result)
            except Exception as e:
                q.put(e)

        process = multiprocessing.Process(target=process_target, args=(context, queue))
        try:
            process.start()
            process.join(self.timeout)

            if process.is_alive():
                logger.error(
                    f"Process execution timed out after {self.timeout} seconds. Terminating process."
                )
                process.terminate()
                process.join()
                msg = f"Process execution timed out after {self.timeout} seconds."
                raise TimeoutError(msg)

            if process.exitcode != 0:
                msg = f"Process failed with exit code {process.exitcode}"
                raise RuntimeError(msg)

            result = queue.get()
            if isinstance(result, Exception):
                raise result
            return result
        finally:
            if process.is_alive():
                process.terminate()
                process.join()
            process.close()
            queue.close()
            queue.join_thread()


class IngestionOrchestrator:
    def __init__(self, deps: PipelineDependencies) -> None:
        self.deps = deps

    def execute(self, context: PipelineContext) -> tuple[typing.Iterator[str], str]:
        import itertools

        if context.file_path:
            preview_chunks = list(
                itertools.islice(self.deps.text_splitter.split_document(context.file_path), 5)
            )
            combined_content = "\n".join(preview_chunks)
            return self.deps.text_splitter.split_document(context.file_path), combined_content
        if context.content:
            return iter(self.deps.text_splitter.split_text(context.content)), context.content

        msg = "PipelineContext must provide either content or file_path"
        raise ValueError(msg)


class AnalysisOrchestrator:
    def __init__(self, deps: PipelineDependencies, config: PipelineConfig) -> None:
        self.deps = deps
        self.config = config

    def execute(
        self,
        context: PipelineContext,
        chunks_iterator: typing.Iterator[str],
        combined_content: str,
    ) -> tuple[dict[str, str], dict[str, str], str]:
        entities = self.deps.entity_extractor.extract_entities(chunks_iterator)

        if context.file_path:
            clustering_iterator = self.deps.text_splitter.split_document(context.file_path)
        else:
            clustering_iterator = iter(self.deps.text_splitter.split_text(context.content))  # type: ignore

        tree_metadata = self.deps.clustering_service.cluster_chunks(
            clustering_iterator, self.config.raptor_max_clusters
        )

        try:
            summary = self.deps.summary_service.generate_summary(combined_content)
        except AIServiceError as e:
            logger.warning(f"Summarization failed: {e}. Using fallback summary.")
            summary = (
                "Fallback Summary: Content processing currently impaired due to AI unavailability."
            )

        return entities, tree_metadata, summary


class OutputOrchestrator:
    def __init__(self, deps: PipelineDependencies) -> None:
        self.deps = deps

    def execute(
        self,
        context: PipelineContext,
        combined_content: str,
        summary: str,
        entities: dict[str, str],
        tree_metadata: dict[str, str],
    ) -> tuple[DocumentNode, Any]:
        root_node = self.deps.doc_factory.create_root_node(
            node_id=context.root_doc_id,
            title="Business Manual",
            content_text=combined_content,
            summary=summary,
        )

        metadata_container = self.deps.metadata_service.create_root_metadata(root_node.id)
        metadata_container.ai_metadata.entity_metadata = entities
        metadata_container.ai_metadata.hierarchical_tree = tree_metadata
        metadata_container.ai_metadata.chunk_id = f"chunk_{context.root_doc_id}"
        metadata_container.ai_metadata.chunk_index = 0

        try:
            question = self.deps.question_service.generate_question(root_node)
            logger.info(f"AI Question: {question}")
        except AIServiceError as e:
            logger.warning(f"Question generation failed: {e}. Skipping interactive prompt loop.")

        return root_node, metadata_container


class PipelineOrchestrator:
    """Handles the high-level orchestration of ingestion, analysis, and output workflows."""

    def __init__(
        self,
        dependencies: PipelineDependencies,
        config: PipelineConfig,
    ) -> None:
        self.deps = dependencies
        self.config = config
        self.process_manager = ProcessManager(timeout=config.pipeline_timeout)
        self.ingestion_orchestrator = IngestionOrchestrator(dependencies)
        self.analysis_orchestrator = AnalysisOrchestrator(dependencies, config)
        self.output_orchestrator = OutputOrchestrator(dependencies)

    def _validate_content_length(self, content: str) -> None:
        if len(content) > self.deps.doc_factory.max_content_length:
            msg = f"Root document content exceeds allowed length of {self.deps.doc_factory.max_content_length} characters."
            raise ValueError(msg)

    def run_pipeline(self, context: PipelineContext) -> None:
        logger.info("Starting document ingestion and analysis pipeline...")
        result = self.process_manager.run_with_timeout(self._execute_pipeline_logic, context)

        if result is not None:
            if isinstance(result, tuple):
                root_node, metadata = result
                self.deps.metadata_service.save_metadata(root_node.id, metadata)
            else:
                root_node = result
            self.deps.doc_repo.save_node(root_node)
            self.deps.transaction_manager.commit()

    def _execute_pipeline_logic(
        self, context: PipelineContext
    ) -> tuple[DocumentNode, Any]:
        try:
            # 1. Ingestion and Semantic Chunking Stage
            logger.info("Ingesting document and performing semantic chunking...")
            chunks_iterator, combined_content = self.ingestion_orchestrator.execute(context)

            # Validate length before ML processing
            self._validate_content_length(combined_content)

            # 2, 3, 4. Analysis Stage
            logger.info("Performing analysis...")
            entities, tree_metadata, summary = self.analysis_orchestrator.execute(
                context, chunks_iterator, combined_content
            )

            # 5. Output Generation Stage
            logger.info("Generating output...")
            root_node, metadata_container = self.output_orchestrator.execute(
                context, combined_content, summary, entities, tree_metadata
            )
        except Exception as e:
            logger.exception("Pipeline execution failed at an intermediate step.")
            msg = f"Pipeline failure: {e}"
            raise RuntimeError(msg) from e
        else:
            logger.info("Pipeline ML logic completed successfully.")
            return root_node, metadata_container
