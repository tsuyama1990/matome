import logging
import sys
from typing import Any

from src.config import ModeConfig, Settings
from src.domain_models.exceptions import ConfigurationError
from src.domain_models.manifest import PipelineContext
from src.infrastructure.orchestrator import (
    PipelineConfig,
    PipelineDependencies,
    PipelineOrchestrator,
)

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Application:
    """Thin application controller responsible only for executing application logic."""

    def __init__(
        self, settings: Settings, mode_config: ModeConfig, orchestrator: PipelineOrchestrator
    ) -> None:
        self.settings = settings
        self.mode_config = mode_config
        self.orchestrator = orchestrator

    def start(self, context: PipelineContext) -> None:
        logger.info(f"Initializing matome application in {self.mode_config.mode} mode...")
        self.orchestrator.run_pipeline(context)


def build_app(
    settings: Settings, mode_config: ModeConfig, deps: PipelineDependencies, config: PipelineConfig
) -> Application:
    """Factory function for bootstrapping components and dependency injection, detached from state."""
    orchestrator = PipelineOrchestrator(dependencies=deps, config=config)
    return Application(settings=settings, mode_config=mode_config, orchestrator=orchestrator)


def get_di_container(settings: Settings) -> Any:
    from src.infrastructure.container import ProductionDIContainer
    from src.application.ai import DefaultAIService
    from src.config import EnvCredentialProvider
    from src.domain_models.services import DocumentFactory, MetadataService
    from src.infrastructure import InMemoryDocumentRepository
    from src.infrastructure.orchestrator import PipelineConfig, PipelineDependencies
    from src.infrastructure.security import PromptInjectionScanner
    from src.infrastructure.services import (
        DefaultClusteringService,
        DefaultTextSplitter,
        LangChainSplitterStrategy,
        RequestsHTTPClient,
        TenacityRetryPolicy,
    )

    repo = InMemoryDocumentRepository()
    ssl_path = settings.ssl_cert_path.get_secret_value() if settings.ssl_cert_path else None
    http_client = RequestsHTTPClient(ssl_cert_path=ssl_path)
    retry_policy = TenacityRetryPolicy(
        ai_retry_attempts=settings.ai_retry_attempts,
        ai_retry_min_wait=settings.ai_retry_min_wait,
        ai_retry_max_wait=settings.ai_retry_max_wait,
    )
    credential_provider = EnvCredentialProvider()
    security_scanner = PromptInjectionScanner()

    from src.infrastructure.ai_client import AIClientFactory
    communication_client = AIClientFactory.create(
        api_url=settings.openrouter_api_url.get_secret_value(),
        default_model=settings.text_fast_model,
        ai_timeout=settings.ai_timeout,
        http_client=http_client,
        retry_policy=retry_policy,
    )

    ai = DefaultAIService(
        security_scanner=security_scanner,
        communication_client=communication_client,
        text_fast_model=settings.text_fast_model,
        text_reasoning_model=settings.text_reasoning_model,
    )

    factory = DocumentFactory()
    metadata_service = MetadataService()

    text_splitter = DefaultTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        max_file_size=settings.max_file_size,
        strategy=LangChainSplitterStrategy(),
    )

    from src.infrastructure.services import EntityExtractorBuilder
    from src.utils.rate_limit import RateLimiter

    entity_extractor = EntityExtractorBuilder.build(
        spacy_model=settings.spacy_model,
        trusted_models=settings.trusted_spacy_models,
        trusted_hashes=settings.trusted_model_hashes,
        fallback_ner_regex=settings.fallback_ner_regex,
        rate_limiter=RateLimiter(settings.entity_extraction_rate_limit),
    )
    clustering_service = DefaultClusteringService(settings.random_seed)

    deps = PipelineDependencies(
        doc_repo=repo,
        transaction_manager=repo,
        summary_service=ai,
        question_service=ai,
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

    return ProductionDIContainer(dependencies=deps, config=config)


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="matome CLI Application")
    parser.add_argument("--file", type=str, help="Path to the document to process", required=True)
    args = parser.parse_args()

    import os

    try:
        try:
            mode = os.getenv("MODE", "cli")
            if mode not in ["cli", "production", "test"]:
                msg = f"Invalid mode: {mode}. Must be one of 'cli', 'production', 'test'."
                raise ValueError(msg)

            filtered_env = {
                k.lower(): v for k, v in os.environ.items() if k.lower() in Settings.model_fields
            }
            settings = Settings(**filtered_env)  # type: ignore[arg-type]
            mode_config = ModeConfig(mode=mode)

            container = get_di_container(settings)
            deps, config = container.get_dependencies()
            app = build_app(settings, mode_config, deps, config)
        except ConfigurationError:
            logger.exception("Configuration Error")
            sys.exit(1)

        allowed_dir = Path(app.settings.allowed_base_dir).resolve()
        file_path = Path(args.file).resolve()

        if not file_path.exists():
            logger.error(f"Failed to execute pipeline: File not found -> {file_path}")
            sys.exit(1)
        if not file_path.is_file():
            logger.error(f"Failed to execute pipeline: Path is not a valid file -> {file_path}")
            sys.exit(1)

        # Prevent directory traversal by checking against configured allowed directory
        real_file_path = str(Path(os.path.realpath(file_path)).resolve())
        real_allowed_dir = str(Path(os.path.realpath(allowed_dir)).resolve())
        if not real_file_path.startswith(real_allowed_dir):
            logger.error("Security Error: Access denied to the requested file.")
            sys.exit(1)

        if file_path.stat().st_size > app.settings.max_file_size:
            logger.error(
                f"Security Error: File exceeds maximum allowed size of {app.settings.max_file_size} bytes -> {file_path}"
            )
            sys.exit(1)

        # Pass the file path to the pipeline for chunked streaming to prevent OOM
        context = PipelineContext(
            root_doc_id=app.settings.default_root_doc_id, file_path=str(file_path)
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
