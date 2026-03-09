import logging
import sys

from src.application.ai import DefaultAIService
from src.config import Settings
from src.domain_models.manifest import PipelineContext
from src.domain_models.services import DocumentFactory, MetadataService
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import (
    PipelineConfig,
    PipelineDependencies,
    PipelineOrchestrator,
)
from src.infrastructure.services import (
    DefaultClusteringService,
    DefaultEntityExtractor,
    DefaultTextSplitter,
    RequestsHTTPClient,
    TenacityRetryPolicy,
)

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Application:
    """Thin application controller responsible only for executing application logic."""

    def __init__(self, settings: Settings, orchestrator: PipelineOrchestrator) -> None:
        self.settings = settings
        self.orchestrator = orchestrator

    def start(self, context: PipelineContext) -> None:
        logger.info(f"Initializing matome application in {self.settings.mode} mode...")
        self.orchestrator.run_pipeline(context)


class AppBuilder:
    """Dedicated factory class for bootstrapping components and dependency injection."""

    @staticmethod
    def build(mode: str = "cli") -> Application:
        import os

        # Initialize Settings directly; pydantic_settings will auto-load os.environ
        # We only override defaults where explicitly passed.
        # Strict validation of OPENROUTER_API_KEY and ALLOWED_BASE_DIR happens inside Settings.
        os.environ["MODE"] = mode

        # Pydantic BaseSettings natively pulls OPENROUTER_API_KEY from env, but type checkers don't know it.
        # It's validated internally via field_validators. We disable type checking on init kwargs.
        settings = Settings()  # type: ignore

        repo = InMemoryDocumentRepository()

        http_client = RequestsHTTPClient()
        retry_policy = TenacityRetryPolicy(
            ai_retry_attempts=settings.ai_retry_attempts,
            ai_retry_min_wait=settings.ai_retry_min_wait,
            ai_retry_max_wait=settings.ai_retry_max_wait,
        )
        ai = DefaultAIService(
            api_key=settings.openrouter_api_key,
            api_url=settings.openrouter_api_url,
            text_fast_model=settings.text_fast_model,
            text_reasoning_model=settings.text_reasoning_model,
            ai_timeout=settings.ai_timeout,
            http_client=http_client,
            retry_policy=retry_policy,
        )
        factory = DocumentFactory()
        metadata_service = MetadataService()
        text_splitter = DefaultTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        entity_extractor = DefaultEntityExtractor(settings.spacy_model)
        clustering_service = DefaultClusteringService(settings.random_seed)

        deps = PipelineDependencies(
            doc_repo=repo,
            transaction_manager=repo,
            ai_service=ai,
            doc_factory=factory,
            metadata_service=metadata_service,
            text_splitter=text_splitter,
            entity_extractor=entity_extractor,
            clustering_service=clustering_service,
        )
        config = PipelineConfig(
            pipeline_timeout=settings.pipeline_timeout,
            raptor_max_clusters=settings.raptor_max_clusters,
        )
        orchestrator = PipelineOrchestrator(dependencies=deps, config=config)
        return Application(settings=settings, orchestrator=orchestrator)


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="matome CLI Application")
    parser.add_argument("--file", type=str, help="Path to the document to process", required=True)
    args = parser.parse_args()

    try:
        from src.domain_models.exceptions import ConfigurationError

        try:
            app = AppBuilder.build(mode="cli")
        except ConfigurationError:
            logger.exception("Configuration Error")
            sys.exit(1)

        allowed_dir = Path(app.settings.allowed_base_dir).resolve()
        file_path = Path(args.file).resolve()

        # Prevent directory traversal by checking against configured allowed directory
        if not file_path.is_relative_to(allowed_dir):
            logger.error(
                f"Security Error: File path must be within the allowed base directory -> {file_path}"
            )
            sys.exit(1)

        if not file_path.exists():
            logger.error(f"Failed to execute pipeline: File not found -> {file_path}")
            sys.exit(1)
        if not file_path.is_file():
            logger.error(f"Failed to execute pipeline: Path is not a valid file -> {file_path}")
            sys.exit(1)

        if file_path.stat().st_size > app.settings.max_file_size:
            logger.error(
                f"Security Error: File exceeds maximum allowed size of {app.settings.max_file_size} bytes -> {file_path}"
            )
            sys.exit(1)

        # Pass the file path to the pipeline for chunked streaming to prevent OOM
        context = PipelineContext(
            root_doc_id=app.settings.default_root_doc_id, content=None, file_path=str(file_path)
        )
        app.start(context)
    except ValueError:
        logger.exception("Configuration or validation error during startup")
        sys.exit(1)
    except RuntimeError:
        logger.exception("Pipeline execution halted due to a runtime error")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unexpected critical failure occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
