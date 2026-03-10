from typing import Protocol

from src.application.ai import DefaultAIService
from src.config import EnvCredentialProvider, Settings
from src.domain_models.interfaces import DocumentRepository
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


class DIContainerProtocol(Protocol):
    def get_dependencies(self) -> tuple[PipelineDependencies, PipelineConfig]: ...


class ProductionDIContainer(DIContainerProtocol):
    def __init__(self, settings: Settings, doc_repo: DocumentRepository | None = None) -> None:
        self.settings = settings
        self.doc_repo = doc_repo or InMemoryDocumentRepository()

    def get_dependencies(self) -> tuple[PipelineDependencies, PipelineConfig]:
        repo = self.doc_repo

        ssl_path = self.settings.ssl_cert_path.get_secret_value() if self.settings.ssl_cert_path else None
        http_client = RequestsHTTPClient(ssl_cert_path=ssl_path)
        retry_policy = TenacityRetryPolicy(
            ai_retry_attempts=self.settings.ai_retry_attempts,
            ai_retry_min_wait=self.settings.ai_retry_min_wait,
            ai_retry_max_wait=self.settings.ai_retry_max_wait,
        )
        EnvCredentialProvider(self.settings.credentials)

        security_scanner = PromptInjectionScanner()
        from src.infrastructure.ai_client import AIClientFactory
        communication_client = AIClientFactory.create(
            api_url=self.settings.openrouter_api_url.get_secret_value(),
            default_model=self.settings.text_fast_model,
            ai_timeout=self.settings.ai_timeout,
            http_client=http_client,
            retry_policy=retry_policy,
        )

        ai = DefaultAIService(
            security_scanner=security_scanner,
            communication_client=communication_client,
            text_fast_model=self.settings.text_fast_model,
            text_reasoning_model=self.settings.text_reasoning_model,
        )
        factory = DocumentFactory()
        metadata_service = MetadataService()

        text_splitter = DefaultTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            max_file_size=self.settings.max_file_size,
            strategy=LangChainSplitterStrategy(),
        )
        from src.infrastructure.services import EntityExtractorBuilder
        from src.utils.rate_limit import RateLimiter

        entity_extractor = EntityExtractorBuilder.build(
            spacy_model=self.settings.spacy_model,
            trusted_models=self.settings.trusted_spacy_models,
            trusted_hashes=self.settings.trusted_model_hashes,
            fallback_ner_regex=self.settings.fallback_ner_regex,
            rate_limiter=RateLimiter(self.settings.entity_extraction_rate_limit),
        )
        clustering_service = DefaultClusteringService(self.settings.random_seed)

        deps = PipelineDependencies(
            doc_repo=repo,
            transaction_manager=repo,  # type: ignore[arg-type]
            summary_service=ai,
            question_service=ai,
            doc_factory=factory,
            metadata_service=metadata_service,
            text_splitter=text_splitter,
            entity_extractor=entity_extractor,
            clustering_service=clustering_service,
        )
        config = PipelineConfig(
            pipeline_timeout=self.settings.pipeline_timeout,
            raptor_max_clusters=self.settings.raptor_max_clusters,
        )

        # Strict DI dependency verification
        for dep_name in [
            "doc_repo",
            "transaction_manager",
            "summary_service",
            "question_service",
            "doc_factory",
            "metadata_service",
            "text_splitter",
            "entity_extractor",
            "clustering_service",
        ]:
            if not getattr(deps, dep_name, None):
                msg = f"DI Container failed to initialize required dependency: {dep_name}"
                raise RuntimeError(msg)

        return deps, config
