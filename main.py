import logging
import sys

from src.config import (
    AIConfig,
    AppContext,
    FileProcessingConfig,
    MLConfig,
    ModeConfig,
    SecurityConfig,
)
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

    def __init__(self, context: AppContext, orchestrator: PipelineOrchestrator) -> None:
        self.context = context
        self.orchestrator = orchestrator

    def start(self, ctx: PipelineContext) -> None:
        logger.info(f"Initializing matome application in {self.context.mode_config.mode} mode...")
        self.orchestrator.run_pipeline(ctx)


def build_app(
    context: AppContext, deps: PipelineDependencies, config: PipelineConfig
) -> Application:
    """Factory function for bootstrapping components and dependency injection, detached from state."""
    orchestrator = PipelineOrchestrator(dependencies=deps, config=config)
    return Application(context=context, orchestrator=orchestrator)


def get_di_container(app_ctx: AppContext) -> DIContainerProtocol:
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
    if "OPENROUTER_API_URL" in os.environ:
        credential_config_args["openrouter_api_url"] = SecretStr(os.environ["OPENROUTER_API_URL"])

    credential_config = CredentialConfig(**credential_config_args)

    repo = InMemoryDocumentRepository()
    ssl_path = os.getenv("SSL_CERT_PATH")

    from src.domain_models.exceptions import ConfigurationError

    if ssl_path:
        from pathlib import Path

        path_obj = Path(ssl_path)
        if not path_obj.is_file() or not os.access(path_obj, os.R_OK):
            msg = f"Invalid SSL_CERT_PATH: {ssl_path}"
            raise ConfigurationError(msg)

    http_client = RequestsHTTPClient(ssl_cert_path=ssl_path)
    retry_policy = TenacityRetryPolicy(
        ai_retry_attempts=app_ctx.ai.ai_retry_attempts,
        ai_retry_min_wait=app_ctx.ai.ai_retry_min_wait,
        ai_retry_max_wait=app_ctx.ai.ai_retry_max_wait,
    )
    security_scanner = PromptInjectionScanner(
        threshold=app_ctx.security.prompt_injection_threshold,
        max_input_length=app_ctx.security.max_input_length,
    )

    from src.infrastructure.ai_client import AIClientFactory

    communication_client = AIClientFactory.create(
        api_url=credential_config.openrouter_api_url.get_secret_value(),
        default_model=app_ctx.ai.text_fast_model,
        ai_timeout=app_ctx.ai.ai_timeout,
        http_client=http_client,
        retry_policy=retry_policy,
        security_scanner=security_scanner,
    )

    summary_service = DefaultSummaryService(
        security_scanner=security_scanner,
        communication_client=communication_client,
        text_fast_model=app_ctx.ai.text_fast_model,
        text_reasoning_model=app_ctx.ai.text_reasoning_model,
    )
    question_service = DefaultQuestionService(
        security_scanner=security_scanner,
        communication_client=communication_client,
        text_fast_model=app_ctx.ai.text_fast_model,
        text_reasoning_model=app_ctx.ai.text_reasoning_model,
    )
    # the rest are not strictly required for PipelineDependencies currently, but keeping pattern

    factory = DocumentFactory()
    metadata_service = MetadataService()

    text_splitter = DefaultTextSplitter(
        chunk_size=app_ctx.file.chunk_size,
        chunk_overlap=app_ctx.file.chunk_overlap,
        max_file_size=app_ctx.file.max_file_size,
        strategy=LangChainSplitterStrategy(),
    )

    from src.infrastructure.services import (
        DefaultModelVerifier,
        EntityExtractorBuilder,
        EntityExtractorBuilderConfig,
    )
    from src.utils.rate_limit import RateLimiter

    builder_config = EntityExtractorBuilderConfig(
        spacy_model=app_ctx.ml.spacy_model,
        trusted_models=app_ctx.ml.trusted_spacy_models,
        trusted_hashes=app_ctx.ml.trusted_model_hashes,
        fallback_ner_regex=app_ctx.ml.fallback_ner_regex,
        max_model_signature_size=app_ctx.security.max_model_signature_size,
    )

    model_verifier = DefaultModelVerifier(
        set(app_ctx.ml.trusted_spacy_models),
        app_ctx.ml.trusted_model_hashes,
        app_ctx.security.max_model_signature_size,
    )
    try:
        model_verifier.verify_model_signature(app_ctx.ml.spacy_model)
        from src.infrastructure.services import SpacyNLPService

        nlp_service = SpacyNLPService(app_ctx.ml.spacy_model)
    except Exception as e:
        logger.warning(f"Failed to load verified spacy model: {e}")
        nlp_service = None

    entity_extractor = EntityExtractorBuilder.build(
        builder_config=builder_config,
        rate_limiter=RateLimiter(app_ctx.ml.entity_extraction_rate_limit),
        nlp_service=nlp_service,
    )
    clustering_service = DefaultClusteringService(app_ctx.ml.random_seed)

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
        pipeline_timeout=app_ctx.pipeline.pipeline_timeout,
        raptor_max_clusters=app_ctx.ml.raptor_max_clusters,
    )

    return ProductionDIContainer(dependencies=deps, config=config)


def setup_config() -> AppContext:
    import os

    mode = os.getenv("MODE", "cli")
    if mode not in ["cli", "production", "test"]:
        msg = f"Invalid mode: {mode}. Must be one of 'cli', 'production', 'test'."
        raise ValueError(msg)

    import typing

    def filter_env(model_cls: typing.Any) -> dict[str, typing.Any]:
        return {k.lower(): v for k, v in os.environ.items() if k.lower() in model_cls.model_fields}

    from src.config import PipelineConfig, create_app_context

    ai_cfg = AIConfig(**filter_env(AIConfig))
    file_cfg = FileProcessingConfig(**filter_env(FileProcessingConfig))
    security_cfg = SecurityConfig(**filter_env(SecurityConfig))
    ml_cfg = MLConfig(**filter_env(MLConfig))
    pipeline_cfg = PipelineConfig(**filter_env(PipelineConfig))
    mode_config = ModeConfig(mode=mode)

    return create_app_context(
        ai=ai_cfg,
        file=file_cfg,
        security=security_cfg,
        ml=ml_cfg,
        pipeline=pipeline_cfg,
        mode_config=mode_config,
    )


def validate_security(app_ctx: AppContext, target_file: str) -> str:
    import os
    from pathlib import Path

    allowed_dir = Path(app_ctx.file.allowed_base_dir).resolve()
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

    if file_path.stat().st_size > app_ctx.file.max_file_size:
        logger.error(
            f"Security Error: File exceeds maximum allowed size of {app_ctx.file.max_file_size} bytes -> {file_path}"
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
            app_ctx = setup_config()
            container = get_di_container(app_ctx)
            deps, config = container.get_dependencies()
            app = build_app(app_ctx, deps, config)
        except ConfigurationError:
            logger.exception("Configuration Error")
            sys.exit(1)

        safe_file_path = validate_security(app.context, args.file)

        # Pass the file path to the pipeline for chunked streaming to prevent OOM
        context = PipelineContext(
            root_doc_id=app.context.pipeline.default_root_doc_id, file_path=safe_file_path
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
