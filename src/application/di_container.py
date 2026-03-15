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
        """Registers a singleton instance for an interface safely across threads."""
        if not isinstance(instance, interface):
            msg = f"Expected instance of {interface}, got {type(instance)}"
            raise TypeError(msg)

        if interface not in self._singletons:
            with self._lock:
                if interface not in self._singletons:
                    self._singletons[interface] = instance

    def register(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Registers a factory function for an interface (resolved as singleton)."""
        with self._lock:
            self._factories[interface] = factory

    def register_scoped(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Registers a factory function for an interface (resolved per-request/scope)."""
        with self._lock:
            self._scoped_factories[interface] = factory

    def _get_resolving_set(self) -> set[type[Any]]:
        if not hasattr(self._local, "resolving"):
            self._local.resolving = set()
        return cast(set[type[Any]], self._local.resolving)

    def resolve(self, interface: type[T]) -> T:
        """Resolves an interface to an instance with circular dependency detection."""
        # Fast path for singletons outside the lock if possible, but we need lock for thread safety
        with self._lock:
            resolving = self._get_resolving_set()

            if interface in resolving:
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

            resolving.add(interface)

        # Call factory inside the lock to ensure atomic singleton creation across threads
        try:
            with self._lock:
                # Double-check inside the lock in case another thread created it
                if not is_scoped and interface in self._singletons:
                    return cast(T, self._singletons[interface])

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
            resolving.remove(interface)

    def close(self) -> None:
        """Properly shuts down and disposes of all singleton instances to prevent memory leaks."""
        with self._lock:
            for instance in self._singletons.values():
                try:
                    if hasattr(instance, "close") and callable(instance.close):
                        instance.close()
                except Exception:  # noqa: S110
                    pass
            self._singletons.clear()

    async def aclose(self) -> None:
        """Asynchronously shuts down all singleton instances, handling async closures."""
        import inspect

        with self._lock:
            instances = list(self._singletons.values())
            self._singletons.clear()

        for instance in instances:
            try:
                if hasattr(instance, "aclose") and callable(instance.aclose):
                    res = instance.aclose()
                    if inspect.isawaitable(res):
                        await res
                elif hasattr(instance, "close") and callable(instance.close):
                    instance.close()
            except Exception:  # noqa: S110
                pass
