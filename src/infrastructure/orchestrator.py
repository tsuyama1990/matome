import enum
import logging
import typing
from typing import Any

from src.domain_models import (
    AIServiceError,
    ClusteringServiceProtocol,
    ContentNode,
    DocumentFactory,
    DocumentRepository,
    EntityExtractorProtocol,
    IdentityNode,
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
    """Handles async-based timeout lifecycle management ensuring resource cleanup without heavy multiprocessing."""

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def run_with_timeout(
        self, target_func: typing.Callable[[PipelineContext], Any], context: PipelineContext
    ) -> Any:
        import asyncio
        import concurrent.futures

        async def _run() -> Any:
            loop = asyncio.get_running_loop()
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                # Use wait_for on the coroutine directly, ensuring graceful dropout upon timeout.
                # shutdown(wait=False, cancel_futures=True) natively prevents the executor from blocking on exit.
                return await asyncio.wait_for(
                    loop.run_in_executor(executor, target_func, context), timeout=self.timeout
                )
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

        try:
            return asyncio.run(_run())
        except TimeoutError as e:
            logger.exception(f"Execution timed out after {self.timeout} seconds.")
            msg = f"Execution timed out after {self.timeout} seconds."
            raise TimeoutError(msg) from e


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
    ) -> tuple[IdentityNode, ContentNode, Any]:
        identity, content = self.deps.doc_factory.create_root_node(
            node_id=context.root_doc_id,
            title="Business Manual",
            content_text=combined_content,
            summary=summary,
        )

        metadata_container = self.deps.metadata_service.create_root_metadata(identity.id)
        metadata_container.ai_metadata.entity_metadata = entities
        metadata_container.ai_metadata.hierarchical_tree = tree_metadata
        metadata_container.ai_metadata.chunk_id = f"chunk_{context.root_doc_id}"
        metadata_container.ai_metadata.chunk_index = 0

        try:
            question = self.deps.question_service.generate_question(identity, content)
            logger.info(f"AI Question: {question}")
        except AIServiceError as e:
            logger.warning(f"Question generation failed: {e}. Skipping interactive prompt loop.")

        return identity, content, metadata_container


class PipelineValidator:
    """Handles logic for validating state inside the pipeline."""

    def __init__(self, doc_factory: DocumentFactory) -> None:
        self.doc_factory = doc_factory

    def validate_content_length(self, content: str) -> None:
        if len(content) > self.doc_factory.max_content_length:
            msg = f"Root document content exceeds allowed length of {self.doc_factory.max_content_length} characters."
            raise ValueError(msg)


class PipelineErrorHandler:
    """Decoupled handler for processing exceptions inside the pipeline executor."""

    @staticmethod
    def handle_execution_error(e: Exception) -> typing.NoReturn:
        logger.exception("Pipeline execution failed at an intermediate step.")
        msg = f"Pipeline failure: {e}"
        raise RuntimeError(msg) from e


class PipelineTransactionManager:
    """Handles the transaction lifecycle of pipeline outputs."""

    def __init__(self, deps: PipelineDependencies) -> None:
        self.deps = deps

    def save_and_commit(self, result: tuple[IdentityNode, ContentNode, Any]) -> None:
        identity, content, metadata = result
        self.deps.metadata_service.save_metadata(identity.id, metadata)
        self.deps.doc_repo.save_identity(identity)
        self.deps.doc_repo.save_content(content)
        self.deps.transaction_manager.commit()


class CircuitBreakerState(enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """A state-managed circuit breaker pattern to properly halt cascading external failures."""

    def __init__(self, threshold: int = 3) -> None:
        self.failures = 0
        self.threshold = threshold
        self.state = CircuitBreakerState.CLOSED

    @property
    def open(self) -> bool:
        return self.state == CircuitBreakerState.OPEN

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.state = CircuitBreakerState.OPEN

    def reset(self) -> None:
        self.failures = 0
        self.state = CircuitBreakerState.CLOSED


class PipelineOrchestrator:
    """Handles the high-level orchestration of ingestion, analysis, and output workflows."""

    def __init__(
        self,
        dependencies: PipelineDependencies,
        config: PipelineConfig,
        **kwargs: Any,
    ) -> None:
        # Dependency Inverted Constructor
        self.deps = dependencies
        self.config = config
        self.process_manager = kwargs.get(
            "process_manager", ProcessManager(timeout=config.pipeline_timeout)
        )
        self.validator = kwargs.get(
            "validator", PipelineValidator(doc_factory=dependencies.doc_factory)
        )
        self.error_handler = kwargs.get("error_handler", PipelineErrorHandler())
        self.transaction_handler = kwargs.get(
            "transaction_handler", PipelineTransactionManager(dependencies)
        )
        self.ingestion_orchestrator = kwargs.get(
            "ingestion_orchestrator", IngestionOrchestrator(dependencies)
        )
        self.analysis_orchestrator = kwargs.get(
            "analysis_orchestrator", AnalysisOrchestrator(dependencies, config)
        )
        self.output_orchestrator = kwargs.get(
            "output_orchestrator", OutputOrchestrator(dependencies)
        )
        self.circuit_breaker = kwargs.get("circuit_breaker", CircuitBreaker())

    def run_pipeline(self, context: PipelineContext) -> None:
        if self.circuit_breaker.open:
            msg = "Circuit breaker is OPEN. Failing fast to prevent cascading system collapse."
            raise RuntimeError(msg)

        logger.info("Starting document ingestion and analysis pipeline...")
        try:
            result = self.process_manager.run_with_timeout(self._execute_pipeline_logic, context)
            self.circuit_breaker.reset()
            if result is not None:
                self.transaction_handler.save_and_commit(result)
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    def _execute_pipeline_logic(
        self, context: PipelineContext
    ) -> tuple[IdentityNode, ContentNode, Any]:
        try:
            # 1. Ingestion and Semantic Chunking Stage
            logger.info("Ingesting document and performing semantic chunking...")
            chunks_iterator, combined_content = self.ingestion_orchestrator.execute(context)

            # Validate length before ML processing
            self.validator.validate_content_length(combined_content)

            # 2, 3, 4. Analysis Stage
            logger.info("Performing analysis...")
            entities, tree_metadata, summary = self.analysis_orchestrator.execute(
                context, chunks_iterator, combined_content
            )

            # 5. Output Generation Stage
            logger.info("Generating output...")
            identity, content, metadata_container = self.output_orchestrator.execute(
                context, combined_content, summary, entities, tree_metadata
            )
        except Exception as e:
            self.error_handler.handle_execution_error(e)
            raise
        else:
            logger.info("Pipeline ML logic completed successfully.")
            return identity, content, metadata_container
