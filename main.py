import logging
import sys

from src.config import ModeConfig, Settings
from src.domain_models.exceptions import ConfigurationError
from src.domain_models.manifest import PipelineContext
from src.infrastructure.container import DIContainerProtocol
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


def get_di_container(settings: Settings) -> DIContainerProtocol:
    import os

    from pydantic import SecretStr

    from src.application.ai import (
        DefaultQuestionService,
        DefaultSummaryService,
    )
    from src.config import CredentialConfig
    from src.domain_models.services import DocumentFactory, MetadataService
    from src.infrastructure import InMemoryDocumentRepository
    from src.infrastructure.container import ProductionDIContainer
    from src.infrastructure.orchestrator import PipelineConfig, PipelineDependencies
    from src.infrastructure.security import PromptInjectionScanner
    from src.infrastructure.services import (
        DefaultClusteringService,
        DefaultTextSplitter,
        LangChainSplitterStrategy,
        RequestsHTTPClient,
        TenacityRetryPolicy,
    )

    # Strictly pull credentials from environment variables avoiding hardcoded fallbacks
    # and ensuring proper instantiation. Let Pydantic Settings handle the presence checks.
    credential_config_args = {}
    if "OPENROUTER_API_KEY" in os.environ:
        credential_config_args["openrouter_api_key"] = SecretStr(os.environ["OPENROUTER_API_KEY"])
    if "OPENROUTER_API_URL" in os.environ:
        credential_config_args["openrouter_api_url"] = SecretStr(os.environ["OPENROUTER_API_URL"])
    if "SSL_CERT_PATH" in os.environ:
        credential_config_args["ssl_cert_path"] = SecretStr(os.environ["SSL_CERT_PATH"])

    credential_config = CredentialConfig(**credential_config_args)

    repo = InMemoryDocumentRepository()
    ssl_path = (
        credential_config.ssl_cert_path.get_secret_value()
        if credential_config.ssl_cert_path
        else None
    )
    http_client = RequestsHTTPClient(ssl_cert_path=ssl_path)
    retry_policy = TenacityRetryPolicy(
        ai_retry_attempts=settings.ai.ai_retry_attempts,
        ai_retry_min_wait=settings.ai.ai_retry_min_wait,
        ai_retry_max_wait=settings.ai.ai_retry_max_wait,
    )
    security_scanner = PromptInjectionScanner(
        threshold=settings.security.prompt_injection_threshold,
        max_input_length=settings.security.max_input_length,
    )

    from src.infrastructure.ai_client import AIClientFactory

    communication_client = AIClientFactory.create(
        api_url=credential_config.openrouter_api_url.get_secret_value(),
        default_model=settings.ai.text_fast_model,
        ai_timeout=settings.ai.ai_timeout,
        http_client=http_client,
        retry_policy=retry_policy,
        security_scanner=security_scanner,
    )

    summary_service = DefaultSummaryService(
        security_scanner=security_scanner,
        communication_client=communication_client,
        text_fast_model=settings.ai.text_fast_model,
        text_reasoning_model=settings.ai.text_reasoning_model,
    )
    question_service = DefaultQuestionService(
        security_scanner=security_scanner,
        communication_client=communication_client,
        text_fast_model=settings.ai.text_fast_model,
        text_reasoning_model=settings.ai.text_reasoning_model,
    )
    # the rest are not strictly required for PipelineDependencies currently, but keeping pattern

    factory = DocumentFactory()
    metadata_service = MetadataService()

    text_splitter = DefaultTextSplitter(
        chunk_size=settings.file.chunk_size,
        chunk_overlap=settings.file.chunk_overlap,
        max_file_size=settings.file.max_file_size,
        strategy=LangChainSplitterStrategy(),
    )

    from src.infrastructure.services import (
        DefaultModelVerifier,
        EntityExtractorBuilder,
        EntityExtractorBuilderConfig,
    )
    from src.utils.rate_limit import RateLimiter

    builder_config = EntityExtractorBuilderConfig(
        spacy_model=settings.ml.spacy_model,
        trusted_models=settings.ml.trusted_spacy_models,
        trusted_hashes=settings.ml.trusted_model_hashes,
        fallback_ner_regex=settings.ml.fallback_ner_regex,
        max_model_signature_size=settings.security.max_model_signature_size,
    )

    entity_extractor = EntityExtractorBuilder.build(
        builder_config=builder_config,
        rate_limiter=RateLimiter(settings.ml.entity_extraction_rate_limit),
        model_verifier=DefaultModelVerifier(
            set(settings.ml.trusted_spacy_models),
            settings.ml.trusted_model_hashes,
            settings.security.max_model_signature_size,
        ),
    )
    clustering_service = DefaultClusteringService(settings.ml.random_seed)

    deps = PipelineDependencies(
        doc_repo=repo,
        transaction_manager=repo,
        summary_service=summary_service,
        question_service=question_service,
        doc_factory=factory,
        metadata_service=metadata_service,
        text_splitter=text_splitter,
        entity_extractor=entity_extractor,
        clustering_service=clustering_service,
    )
    config = PipelineConfig(
        pipeline_timeout=settings.pipeline.pipeline_timeout,
        raptor_max_clusters=settings.ml.raptor_max_clusters,
    )

    return ProductionDIContainer(dependencies=deps, config=config)


def setup_config() -> tuple[Settings, ModeConfig]:
    import os

    mode = os.getenv("MODE", "cli")
    if mode not in ["cli", "production", "test"]:
        msg = f"Invalid mode: {mode}. Must be one of 'cli', 'production', 'test'."
        raise ValueError(msg)

    filtered_env = {
        k.lower(): v for k, v in os.environ.items() if k.lower() in Settings.model_fields
    }
    settings = Settings(**filtered_env)  # type: ignore[arg-type]
    mode_config = ModeConfig(mode=mode)
    return settings, mode_config


def validate_security(settings: Settings, target_file: str) -> str:
    import os
    from pathlib import Path

    allowed_dir = Path(settings.file.allowed_base_dir).resolve()
    file_path = Path(target_file).resolve()

    if not file_path.exists():
        logger.error(f"Failed to execute pipeline: File not found -> {file_path}")
        sys.exit(1)
    if not file_path.is_file():
        logger.error(f"Failed to execute pipeline: Path is not a valid file -> {file_path}")
        sys.exit(1)

    # Prevent directory traversal by checking against configured allowed directory
    real_file_path = Path(os.path.realpath(file_path)).resolve()
    real_allowed_dir = Path(os.path.realpath(allowed_dir)).resolve()

    if not real_file_path.is_relative_to(real_allowed_dir):
        logger.error("Security Error: Access denied to the requested file.")
        sys.exit(1)

    if file_path.stat().st_size > settings.file.max_file_size:
        logger.error(
            f"Security Error: File exceeds maximum allowed size of {settings.file.max_file_size} bytes -> {file_path}"
        )
        sys.exit(1)

    return str(file_path)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="matome CLI Application")
    parser.add_argument("--file", type=str, help="Path to the document to process", required=True)
    args = parser.parse_args()

    try:
        try:
            settings, mode_config = setup_config()
            container = get_di_container(settings)
            deps, config = container.get_dependencies()
            app = build_app(settings, mode_config, deps, config)
        except ConfigurationError:
            logger.exception("Configuration Error")
            sys.exit(1)

        safe_file_path = validate_security(app.settings, args.file)

        # Pass the file path to the pipeline for chunked streaming to prevent OOM
        context = PipelineContext(
            root_doc_id=app.settings.pipeline.default_root_doc_id, file_path=safe_file_path
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
