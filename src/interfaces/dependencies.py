import importlib
import logging
import threading
import uuid
from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

from src.domain_models.document import SemanticChunk
from src.domain_models.pivot import PivotRequestPayload, PivotResponse

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMProtocol(Protocol):
    """Protocol for interacting with LLM Gateways."""

    async def generate(self, prompt: str) -> str: ...

    async def generate_text(self, prompt: str, model: str) -> str: ...


@runtime_checkable
class VectorDBProtocol(Protocol):
    """Protocol defining the contract for similarity search."""

    async def upsert(self, chunks: list[SemanticChunk]) -> None: ...

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter_metadata: dict[str, str] | None = None,
    ) -> list[SemanticChunk]: ...


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Protocol for interacting with Vector Databases."""

    def upsert(self, collection_name: str, records: list[dict[str, Any]]) -> None: ...

    def search(
        self, collection_name: str, query_vector: list[float], limit: int
    ) -> list[dict[str, Any]]: ...


@runtime_checkable
class EmbeddingProtocol(Protocol):
    """Protocol for generating vector embeddings."""

    async def embed_text(self, text: str) -> list[float]: ...


@runtime_checkable
class PivotWorkflowProtocol(Protocol):
    """Protocol defining the facade for Pivot Workflow orchestration."""

    async def execute(
        self, document_id: uuid.UUID, payload: PivotRequestPayload
    ) -> PivotResponse: ...


@runtime_checkable
class TextParserProtocol(Protocol):
    """Protocol for extracting raw string content from various document formats."""

    async def parse(self, file_content: bytes, filename: str) -> str: ...


T = TypeVar("T")


class DIContainer:
    """Dependency Injection container using dynamic imports for initialization."""

    def __init__(self) -> None:
        self._factories: dict[type[Any], Callable[[], Any]] = {}
        self._singletons: dict[type[Any], Any] = {}
        self._lock = threading.RLock()
        self._local = threading.local()

    def _get_resolving_set(self) -> set[type[Any]]:
        if not hasattr(self._local, "resolving"):
            self._local.resolving = set()
        return self._local.resolving  # type: ignore[no-any-return]

    def register(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Registers a factory function for an interface."""
        with self._lock:
            self._factories[interface] = factory

    def resolve(self, interface: type[T]) -> T:
        """Resolves an interface to its singleton instance with circular dependency detection."""
        with self._lock:
            if interface in self._singletons:
                return self._singletons[interface]  # type: ignore[no-any-return]

            resolving = self._get_resolving_set()

            if interface in resolving:
                msg = f"Circular dependency detected while resolving: {interface}"
                raise RuntimeError(msg)

            if interface not in self._factories:
                msg = f"Dependency not registered: {interface}"
                raise RuntimeError(msg)

            resolving.add(interface)
            try:
                # We do not hold the lock during factory instantiation to avoid deadlocks
                # if factory also calls resolve. But wait, if factory calls resolve, it re-enters.
                # Re-entrant locks or maintaining tracking thread-locally is better,
                # but for this scale, simply tracking during the single traversal is fine.
                instance = self._factories[interface]()
                self._singletons[interface] = instance
                return instance  # type: ignore[no-any-return]
            finally:
                resolving.remove(interface)

    def load_dynamic_class(self, module_path: str, class_name: str) -> type[Any]:
        """Dynamically loads a class from a module."""
        module = importlib.import_module(module_path)
        return getattr(module, class_name)  # type: ignore[no-any-return]


def validate_container(container: DIContainer) -> None:
    """Validates that necessary protocols are registered."""
    required_protocols = [LLMProtocol, VectorStoreProtocol]
    missing = []
    for protocol in required_protocols:
        if protocol not in container._factories and protocol not in container._singletons:
            missing.append(protocol.__name__)

    if missing:
        msg = (
            f"Critical dependencies missing: {', '.join(missing)}. Please check App initialization."
        )
        logger.error(msg)
        raise RuntimeError(msg)


def register_raptor_engine(container: DIContainer) -> None:
    from src.application import RaptorEngine
    from src.config.settings import AppConfig

    def raptor_factory() -> RaptorEngine:
        from src.infrastructure.clustering import UMAPGMMClusteringStrategy
        from src.interfaces.clustering import ClusteringStrategy

        if (
            ClusteringStrategy not in container._factories
            and ClusteringStrategy not in container._singletons
        ):
            try:
                import umap.umap_ as umap
                from sklearn.mixture import GaussianMixture

                umap_lib = umap
                gmm_cls = GaussianMixture
            except ImportError:
                umap_lib = None
                gmm_cls = None

            def _clustering_factory() -> ClusteringStrategy:
                return UMAPGMMClusteringStrategy(umap_lib=umap_lib, gmm_cls=gmm_cls)

            container.register(ClusteringStrategy, _clustering_factory)  # type: ignore[type-abstract]

        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        clustering_strategy = container.resolve(ClusteringStrategy)  # type: ignore[type-abstract]
        config = container.resolve(AppConfig)
        return RaptorEngine(
            llm=llm,
            clustering_strategy=clustering_strategy,
            max_clusters=config.raptor_max_clusters,
            max_content_length=config.max_content_length,
        )

    container.register(RaptorEngine, raptor_factory)


def register_sq3r_engine(container: DIContainer) -> None:
    from src.application import SQ3REngine

    def sq3r_factory() -> SQ3REngine:
        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        return SQ3REngine(llm=llm)

    container.register(SQ3REngine, sq3r_factory)


def register_pivot_workflow(container: DIContainer) -> None:
    from src.application.pivot_workflow import ExportService, PivotEngine, PivotWorkflow
    from src.interfaces.repository import DocumentRepositoryProtocol

    # If the user overrides PivotEngine directly, don't try to resolve its internal dependencies
    if PivotEngine not in container._factories and PivotEngine not in container._singletons:

        def pivot_engine_factory() -> PivotEngine:
            from src.config.settings import AppConfig

            config = container.resolve(AppConfig)
            llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
            vector_db = container.resolve(VectorDBProtocol)  # type: ignore[type-abstract]
            embedding = container.resolve(EmbeddingProtocol)  # type: ignore[type-abstract]
            return PivotEngine(
                llm=llm,
                vector_db=vector_db,
                embedding=embedding,
                allowed_axes=frozenset(config.pivot_allowed_axes),
                llm_timeout=config.llm_timeout,
            )

        container.register(PivotEngine, pivot_engine_factory)

    if ExportService not in container._factories and ExportService not in container._singletons:

        def export_service_factory() -> ExportService:
            return ExportService()

        container.register(ExportService, export_service_factory)

    def pivot_workflow_factory() -> PivotWorkflowProtocol:
        repository = container.resolve(DocumentRepositoryProtocol)  # type: ignore[type-abstract]
        pivot_engine_new = container.resolve(PivotEngine)
        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        return PivotWorkflow(repository=repository, pivot_engine=pivot_engine_new, llm=llm)

    container.register(PivotWorkflowProtocol, pivot_workflow_factory)  # type: ignore[type-abstract]


def register_vector_store(container: DIContainer) -> None:
    import os

    from src.infrastructure.vector_store import PineconeVectorStore

    def vector_store_factory() -> VectorStoreProtocol:
        api_key = os.environ.get("PINECONE_API_KEY")
        if not api_key:
            from src.infrastructure.vector_store import InMemoryVectorStore

            logger.warning("PINECONE_API_KEY not found, falling back to InMemoryVectorStore.")
            return InMemoryVectorStore()

        environment = os.environ.get("PINECONE_ENV", "us-east-1")
        index_name = os.environ.get("PINECONE_INDEX", "matome")
        return PineconeVectorStore(api_key, environment, index_name)

    container.register(VectorStoreProtocol, vector_store_factory)  # type: ignore[type-abstract]

    def vector_db_factory() -> VectorDBProtocol:
        from src.infrastructure.vector_store import VectorDBAdapter

        store = container.resolve(VectorStoreProtocol)  # type: ignore[type-abstract]
        return VectorDBAdapter(vector_store=store)

    container.register(VectorDBProtocol, vector_db_factory)  # type: ignore[type-abstract]


def _load_spacy_model(model_name: str) -> Any | None:
    try:
        import spacy

        return spacy.load(model_name)
    except (ImportError, OSError):
        logger.warning(f"Spacy model '{model_name}' not found. Falling back to simple processing.")
        return None


def register_nlp_service(container: DIContainer) -> None:
    from src.application import NLPService
    from src.config.settings import AppConfig

    def nlp_factory() -> NLPService:
        config = container.resolve(AppConfig)

        nlp_model = _load_spacy_model(config.spacy_model)

        return NLPService(
            nlp_model=nlp_model,
            max_entities=config.nlp_max_entities,
            time_axis_past_words=config.nlp_time_axis_past_words,
            time_axis_future_words=config.nlp_time_axis_future_words,
            max_content_length=config.max_content_length,
        )

    container.register(NLPService, nlp_factory)


def _register_core_infrastructure(container: DIContainer) -> None:
    try:
        register_vector_store(container)
    except Exception as e:
        logger.exception("Vector store registration failed.")
        msg = "Bootstrap failed due to core infrastructure failure."
        raise RuntimeError(msg) from e


def register_ingestion_pipeline(container: DIContainer) -> None:
    from src.application import IngestionPipeline, RaptorEngine
    from src.config.settings import AppConfig as SettingsAppConfig
    from src.domain_models.config import AppConfig as DomainAppConfig

    def ingestion_factory() -> IngestionPipeline:
        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        embedding = container.resolve(EmbeddingProtocol)  # type: ignore[type-abstract]
        text_parser = container.resolve(TextParserProtocol)  # type: ignore[type-abstract]
        raptor_engine = container.resolve(RaptorEngine)

        try:
            settings_config = container.resolve(SettingsAppConfig)
            max_sentences = getattr(settings_config, "max_sentences_per_chunk", 5)
            spacy_model_name = settings_config.spacy_model
        except Exception:
            max_sentences = 5
            spacy_model_name = "en_core_web_sm"

        try:
            domain_config = container.resolve(DomainAppConfig)
            fast_model = domain_config.routing_rules.text_fast_model
        except Exception:
            fast_model = "default"

        nlp_model = _load_spacy_model(spacy_model_name)

        return IngestionPipeline(
            llm=llm,
            embedding=embedding,
            text_parser=text_parser,
            raptor_engine=raptor_engine,
            fast_model_name=fast_model,
            nlp_model=nlp_model,
            max_sentences_per_chunk=max_sentences,
        )

    container.register(IngestionPipeline, ingestion_factory)


def _register_application_services(container: DIContainer) -> None:
    try:
        register_raptor_engine(container)
    except Exception:
        logger.exception(
            "RaptorEngine failed to register. Document summarizing will be unavailable."
        )

    try:
        register_sq3r_engine(container)
    except Exception:
        logger.exception(
            "SQ3REngine failed to register. Interactive questioning will be unavailable."
        )

    try:
        register_pivot_workflow(container)
    except Exception as e:
        logger.exception("PivotWorkflow failed to register. Pivot API features will be degraded.")
        msg = "Critical registration failure for PivotWorkflow"
        raise RuntimeError(msg) from e

    try:
        register_nlp_service(container)
    except Exception:
        logger.exception("NLPService failed to register. Entity tagging will fail.")

    try:
        register_ingestion_pipeline(container)
    except Exception:
        logger.exception("IngestionPipeline failed to register. Document ingestion will fail.")


def bootstrap_application_services(container: DIContainer) -> None:
    """Helper to cleanly register application services to the DI container."""
    logger.info("Starting bootstrap of application services...")

    # Pre-Core Validation (Per audit requirements)
    try:
        validate_container(container)
    except Exception as e:
        logger.exception("Container pre-validation failed.")
        msg = "Bootstrap failed."
        raise RuntimeError(msg) from e

    # Core Infrastructure
    _register_core_infrastructure(container)

    # Domain Services
    _register_application_services(container)

    logger.info("Bootstrap complete.")
