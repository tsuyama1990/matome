import importlib
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


class DocumentParserProtocol(Protocol):
    """Protocol for parsing raw files into strings."""

    def parse(self, filepath: str) -> str: ...


class ChunkingProtocol(Protocol):
    """Protocol for breaking text into semantic chunks."""

    def chunk_text(self, text: str, source_file: str) -> list[Any]: ...


T = TypeVar("T")


class DIContainer:
    """Dependency Injection container using dynamic imports for initialization."""

    def __init__(self) -> None:
        self._factories: dict[type[Any], Callable[[], Any]] = {}
        self._singletons: dict[type[Any], Any] = {}

    def register(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Registers a factory function for an interface."""
        self._factories[interface] = factory

    def resolve(self, interface: type[T]) -> T:
        """Resolves an interface to its singleton instance."""
        if interface in self._singletons:
            return self._singletons[interface]  # type: ignore[no-any-return]

        if interface not in self._factories:
            msg = f"Dependency not registered: {interface}"
            raise RuntimeError(msg)

        instance = self._factories[interface]()

        self._singletons[interface] = instance
        return instance  # type: ignore[no-any-return]

    def load_dynamic_class(self, module_path: str, class_name: str) -> type[Any]:
        """Dynamically loads a class from a module."""
        module = importlib.import_module(module_path)
        return getattr(module, class_name)  # type: ignore[no-any-return]
