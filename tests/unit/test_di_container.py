import threading
import time

import pytest

from src.application.di_container import DIContainer
from src.interfaces.llm_protocol import LLMProtocol


class FallbackLLM:
    async def generate_text(self, prompt: str, model: str) -> str:
        return "fallback"


def test_di_container_register_resolve_singleton() -> None:
    container = DIContainer()
    instance = FallbackLLM()

    container.register_singleton(LLMProtocol, instance)  # type: ignore[type-abstract]
    resolved = container.resolve(LLMProtocol)  # type: ignore[type-abstract]

    assert resolved is instance


def test_di_container_register_resolve_factory() -> None:
    container = DIContainer()

    def factory() -> FallbackLLM:
        return FallbackLLM()

    container.register(LLMProtocol, factory)  # type: ignore[type-abstract]
    resolved1 = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
    resolved2 = container.resolve(LLMProtocol)  # type: ignore[type-abstract]

    assert isinstance(resolved1, FallbackLLM)
    assert resolved1 is resolved2


def test_di_container_unregistered() -> None:
    container = DIContainer()

    with pytest.raises(RuntimeError, match="Dependency not registered"):
        container.resolve(LLMProtocol)  # type: ignore[type-abstract]


class ServiceA:
    def __init__(self, b: "ServiceB") -> None:
        self.b = b


class ServiceB:
    def __init__(self, a: "ServiceA") -> None:
        self.a = a


def test_di_container_circular_dependency() -> None:
    container = DIContainer()

    def factory_a() -> ServiceA:
        b = container.resolve(ServiceB)
        return ServiceA(b)

    def factory_b() -> ServiceB:
        a = container.resolve(ServiceA)
        return ServiceB(a)

    container.register(ServiceA, factory_a)
    container.register(ServiceB, factory_b)

    with pytest.raises(RuntimeError, match="Circular dependency detected"):
        container.resolve(ServiceA)


def test_di_container_thread_safety() -> None:
    container = DIContainer()

    def slow_factory() -> FallbackLLM:
        time.sleep(0.1)
        return FallbackLLM()

    container.register(LLMProtocol, slow_factory)  # type: ignore[type-abstract]

    results = []

    def worker() -> None:
        try:
            res = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
            results.append(res)
        except Exception as e:
            results.append(e)  # type: ignore[arg-type]

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The factory takes 0.1s. It should only be called once, because the first thread takes the lock,
    # executes it, registers it as singleton, and the subsequent threads get the singleton.
    # Wait, DIContainer's resolve method:
    # Because lock is held during this, it's thread-safe.

    assert len(results) == 5
    first_res = results[0]
    for r in results:
        assert isinstance(r, FallbackLLM)
        assert r is first_res
