import pytest

from src.interfaces.dependencies import DIContainer


class DummyInterface:
    def do_something(self) -> str:
        return "Not implemented"


class DummyImplementation(DummyInterface):
    def do_something(self) -> str:
        return "Success"


def test_di_container_registers_and_resolves() -> None:
    """Test standard registering and resolving from DI container."""
    container = DIContainer()
    container.register(DummyInterface, DummyImplementation)

    instance = container.resolve(DummyInterface)

    assert isinstance(instance, DummyImplementation)
    assert instance.do_something() == "Success"


def test_di_container_resolves_singletons() -> None:
    """Test DI container uses singleton logic."""
    container = DIContainer()
    container.register(DummyInterface, DummyImplementation)

    instance_1 = container.resolve(DummyInterface)
    instance_2 = container.resolve(DummyInterface)

    # They should be the exact same instance in memory
    assert id(instance_1) == id(instance_2)


def test_di_container_raises_on_unregistered_interface() -> None:
    """Test a RuntimeError is raised if attempting to resolve unregistered interfaces."""
    container = DIContainer()

    with pytest.raises(RuntimeError) as excinfo:
        container.resolve(DummyInterface)

    assert f"Dependency not registered: {DummyInterface}" in str(excinfo.value)


def test_di_container_loads_dynamic_class() -> None:
    """Test dynamically loading a class works correctly."""
    container = DIContainer()

    loaded_class = container.load_dynamic_class("src.interfaces.dependencies", "DIContainer")
    assert loaded_class is DIContainer
