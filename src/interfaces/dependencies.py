import importlib
import logging
import threading
from collections.abc import Callable
from typing import Any, Protocol, TypeVar, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMProtocol(Protocol):
    """Protocol for interacting with LLM Gateways."""

    async def generate(self, prompt: str) -> str: ...

    async def generate_text(self, prompt: str, model: str) -> str: ...


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
        self._resolving: set[type[Any]] = set()

    def register(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Registers a factory function for an interface."""
        with self._lock:
            self._factories[interface] = factory

    def resolve(self, interface: type[T]) -> T:
        """Resolves an interface to its singleton instance with circular dependency detection."""
        with self._lock:
            if interface in self._singletons:
                return self._singletons[interface]  # type: ignore[no-any-return]

            if interface in self._resolving:
                msg = f"Circular dependency detected while resolving: {interface}"
                raise RuntimeError(msg)

            if interface not in self._factories:
                msg = f"Dependency not registered: {interface}"
                raise RuntimeError(msg)

            self._resolving.add(interface)
            try:
                # We do not hold the lock during factory instantiation to avoid deadlocks
                # if factory also calls resolve. But wait, if factory calls resolve, it re-enters.
                # Re-entrant locks or maintaining tracking thread-locally is better,
                # but for this scale, simply tracking during the single pass is fine.
                instance = self._factories[interface]()
                self._singletons[interface] = instance
                return instance  # type: ignore[no-any-return]
            finally:
                self._resolving.remove(interface)

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
    from src.application import RAPTOREngine
    from src.config.settings import AppConfig

    def raptor_factory() -> RAPTOREngine:
        from src.infrastructure.clustering import UMAPGMMClusteringStrategy
        from src.interfaces.clustering import ClusteringStrategy

        if (
            ClusteringStrategy not in container._factories
            and ClusteringStrategy not in container._singletons
        ):
            container.register(ClusteringStrategy, UMAPGMMClusteringStrategy)  # type: ignore[type-abstract]

        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        clustering_strategy = container.resolve(ClusteringStrategy)  # type: ignore[type-abstract]
        config = container.resolve(AppConfig)
        return RAPTOREngine(
            llm=llm,
            clustering_strategy=clustering_strategy,
            max_levels=config.raptor_max_levels,
            max_clusters=config.raptor_max_clusters,
        )

    container.register(RAPTOREngine, raptor_factory)


def register_sq3r_engine(container: DIContainer) -> None:
    from src.application import SQ3REngine

    def sq3r_factory() -> SQ3REngine:
        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        return SQ3REngine(llm=llm)

    container.register(SQ3REngine, sq3r_factory)


def register_pivot_kj_engine(container: DIContainer) -> None:
    from src.application import PivotKJEngine
    from src.config.settings import AppConfig

    def pivot_factory() -> PivotKJEngine:
        config = container.resolve(AppConfig)
        return PivotKJEngine(allowed_axes=frozenset(config.pivot_allowed_axes))

    container.register(PivotKJEngine, pivot_factory)


def register_pivot_workflow(container: DIContainer) -> None:
    from src.application.pivot_workflow import PivotWorkflow
    from src.interfaces.repository import DocumentRepositoryProtocol

    def pivot_workflow_factory() -> PivotWorkflow:
        from src.application import PivotKJEngine

        repository = container.resolve(DocumentRepositoryProtocol)  # type: ignore[type-abstract]
        pivot_engine = container.resolve(PivotKJEngine)
        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        return PivotWorkflow(repository=repository, pivot_engine=pivot_engine, llm=llm)

    container.register(PivotWorkflow, pivot_workflow_factory)


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


def register_nlp_service(container: DIContainer) -> None:
    from src.application import NLPService
    from src.config.settings import AppConfig

    def nlp_factory() -> NLPService:
        config = container.resolve(AppConfig)
        return NLPService(
            model_name=config.spacy_model,
            max_entities=config.nlp_max_entities,
            time_axis_past_words=config.nlp_time_axis_past_words,
            time_axis_future_words=config.nlp_time_axis_future_words,
        )

    container.register(NLPService, nlp_factory)


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
    try:
        register_vector_store(container)
    except Exception as e:
        logger.exception("Vector store registration failed.")
        msg = "Bootstrap failed due to core infrastructure failure."
        raise RuntimeError(msg) from e

    try:
        register_raptor_engine(container)
    except Exception:
        logger.exception(
            "RAPTOREngine failed to register. Document summarizing will be unavailable."
        )

    try:
        register_sq3r_engine(container)
    except Exception:
        logger.exception(
            "SQ3REngine failed to register. Interactive questioning will be unavailable."
        )

    try:
        register_pivot_kj_engine(container)
    except Exception:
        logger.exception(
            "PivotKJEngine failed to register. Pivot KJ clustering will be unavailable."
        )

    try:
        register_pivot_workflow(container)
    except Exception:
        logger.exception("PivotWorkflow failed to register. Pivot API features will be degraded.")

    try:
        register_nlp_service(container)
    except Exception:
        logger.exception("NLPService failed to register. Entity tagging will fail.")

    logger.info("Bootstrap complete.")
