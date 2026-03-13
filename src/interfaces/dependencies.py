import importlib
import threading
from collections.abc import Callable
from typing import Any, Protocol, TypeVar


class LLMProtocol(Protocol):
    """Protocol for interacting with LLM Gateways."""

    async def generate(self, prompt: str) -> str: ...


class VectorStoreProtocol(Protocol):
    """Protocol for interacting with Vector Databases."""

    def upsert(self, collection_name: str, records: list[dict[str, Any]]) -> None: ...

    def search(
        self, collection_name: str, query_vector: list[float], limit: int
    ) -> list[dict[str, Any]]: ...


T = TypeVar("T")


class DIContainer:
    """Dependency Injection container using dynamic imports for initialization."""

    def __init__(self) -> None:
        self._factories: dict[type[Any], Callable[[], Any]] = {}
        self._singletons: dict[type[Any], Any] = {}
        self._lock = threading.Lock()
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


def bootstrap_application_services(container: DIContainer) -> None:
    """Helper to cleanly register application services to the DI container."""
    from src.application import NLPService, PivotKJEngine, RAPTOREngine, SQ3REngine
    from src.config.settings import AppConfig

    # Validate essential configurations and protocols exist prior to booting engines.
    if LLMProtocol not in container._factories and LLMProtocol not in container._singletons:
        msg = "LLMProtocol must be registered in the DI container before bootstrapping application services."
        raise RuntimeError(msg)

    # Register RAPTOREngine
    def raptor_factory() -> RAPTOREngine:
        from src.infrastructure.clustering import UMAPGMMClusteringStrategy
        from src.interfaces.clustering import ClusteringStrategy

        # In a real app we'd resolve it, but for simplicity here we can just instantiate or resolve
        if (
            ClusteringStrategy not in container._factories
            and ClusteringStrategy not in container._singletons
        ):
            container.register(ClusteringStrategy, UMAPGMMClusteringStrategy)  # type: ignore[type-abstract]

        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        clustering_strategy = container.resolve(ClusteringStrategy)  # type: ignore[type-abstract]
        return RAPTOREngine(llm=llm, clustering_strategy=clustering_strategy)

    container.register(RAPTOREngine, raptor_factory)

    # Register SQ3REngine
    def sq3r_factory() -> SQ3REngine:
        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        return SQ3REngine(llm=llm)

    container.register(SQ3REngine, sq3r_factory)

    # Register PivotKJEngine
    container.register(PivotKJEngine, PivotKJEngine)

    # Register NLPService
    def nlp_factory() -> NLPService:
        config = container.resolve(AppConfig)
        return NLPService(model_name=config.spacy_model)

    container.register(NLPService, nlp_factory)
