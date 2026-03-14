import threading
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

class DIContainer:
    """Dependency Injection container using dynamic imports for initialization."""

    def __init__(self) -> None:
        self._factories: dict[type[Any], Callable[[], Any]] = {}
        self._singletons: dict[type[Any], Any] = {}
        self._lock = threading.RLock()
        self._resolving: set[type[Any]] = set()

    def register_singleton(self, interface: type[T], instance: T) -> None:
        """Registers a singleton instance for an interface."""
        with self._lock:
            self._singletons[interface] = instance

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
                instance = self._factories[interface]()
                self._singletons[interface] = instance
                return instance  # type: ignore[no-any-return]
            finally:
                self._resolving.remove(interface)
