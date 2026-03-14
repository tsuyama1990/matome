import threading
from collections.abc import Callable
from typing import Any, TypeVar, cast

T = TypeVar("T")


class DIContainer:
    """Dependency Injection container using dynamic imports for initialization."""

    def __init__(self) -> None:
        self._factories: dict[type[Any], Callable[[], Any]] = {}
        self._singletons: dict[type[Any], Any] = {}
        self._scoped_factories: dict[type[Any], Callable[[], Any]] = {}
        self._lock = threading.RLock()
        self._local = threading.local()

    def register_singleton(self, interface: type[T], instance: T) -> None:
        """Registers a singleton instance for an interface."""
        if not isinstance(instance, interface):
            msg = f"Expected instance of {interface}, got {type(instance)}"
            raise TypeError(msg)
        with self._lock:
            self._singletons[interface] = instance

    def register(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Registers a factory function for an interface (resolved as singleton)."""
        with self._lock:
            self._factories[interface] = factory

    def register_scoped(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Registers a factory function for an interface (resolved per-request/scope)."""
        with self._lock:
            self._scoped_factories[interface] = factory

    def resolve(self, interface: type[T]) -> T:
        """Resolves an interface to an instance with circular dependency detection."""
        with self._lock:
            if not hasattr(self._local, "resolving"):
                self._local.resolving = set()

            if interface in self._local.resolving:
                msg = f"Circular dependency detected while resolving: {interface}"
                raise RuntimeError(msg)

            if interface in self._singletons:
                if not isinstance(self._singletons[interface], interface):
                    msg = f"Expected {interface}, got {type(self._singletons[interface])}"
                    raise TypeError(msg)
                return cast(T, self._singletons[interface])

            is_scoped = interface in self._scoped_factories
            is_singleton = interface in self._factories

            if not is_scoped and not is_singleton:
                msg = f"Dependency not registered: {interface}"
                raise RuntimeError(msg)

            factory = self._scoped_factories[interface] if is_scoped else self._factories[interface]

            self._local.resolving.add(interface)
            try:
                try:
                    instance = factory()
                except Exception as e:
                    msg = f"Error instantiating dependency {interface}: {e}"
                    raise RuntimeError(msg) from e

                if not isinstance(instance, interface):
                    msg = f"Expected {interface}, got {type(instance)}"
                    raise TypeError(msg)

                if not is_scoped:
                    self._singletons[interface] = instance

                return instance
            finally:
                self._local.resolving.remove(interface)
