import logging
import sys

from src.application.ai import DefaultAIService
from src.config import Settings
from src.domain_models.manifest import PipelineContext
from src.domain_models.services import DocumentFactory
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import PipelineOrchestrator
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

        from pydantic import SecretStr

        api_key_str = os.getenv("OPENROUTER_API_KEY")
        api_key = SecretStr(api_key_str) if api_key_str else None

        from pathlib import Path
        settings = Settings(
            mode=mode,
            openrouter_api_key=api_key,
            openrouter_api_url=os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions"),
            text_fast_model=os.getenv("TEXT_FAST_MODEL", "google/gemini-2.5-flash"),
            text_reasoning_model=os.getenv("TEXT_REASONING_MODEL", "deepseek/deepseek-reasoner"),
            multimodal_model=os.getenv("MULTIMODAL_MODEL", "openai/gpt-4o"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100")),
            raptor_max_clusters=int(os.getenv("RAPTOR_MAX_CLUSTERS", "5")),
            pipeline_timeout=float(os.getenv("PIPELINE_TIMEOUT", "300.0")),
            ai_timeout=int(os.getenv("AI_TIMEOUT", "10")),
            max_file_size=int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024))),
            allowed_base_dir=os.getenv("ALLOWED_BASE_DIR", str(Path.cwd().resolve()))
        )

        if not settings.openrouter_api_key:
            logger.error("Configuration Error: OPENROUTER_API_KEY is required to start the application.")
            sys.exit(1)

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
        text_splitter = DefaultTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        entity_extractor = DefaultEntityExtractor()
        clustering_service = DefaultClusteringService()

        orchestrator = PipelineOrchestrator(
            doc_repo=repo,
            ai_service=ai,
            doc_factory=factory,
            text_splitter=text_splitter,
            entity_extractor=entity_extractor,
            clustering_service=clustering_service,
            pipeline_timeout=settings.pipeline_timeout,
            raptor_max_clusters=settings.raptor_max_clusters,
        )
        return Application(settings=settings, orchestrator=orchestrator)


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="matome CLI Application")
    parser.add_argument("--file", type=str, help="Path to the document to process", required=True)
    args = parser.parse_args()

    try:
        app = AppBuilder.build(mode="cli")

        file_path = Path(args.file).resolve()
        allowed_dir = Path(app.settings.allowed_base_dir).resolve()

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
            root_doc_id=app.settings.default_root_doc_id,
            content=None,
            file_path=str(file_path)
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
