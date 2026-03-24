# CYCLE 01: Core Domain Models & Configuration Foundation

## Summary
This first development cycle focuses on establishing the absolute foundation of the `matome` architecture. Before any complex AI orchestration or dynamic user interfaces can be built, the system requires a rock-solid, type-safe representation of its core concepts and configuration parameters. We will achieve this by creating robust Pydantic models that define the application's configuration state, including essential aspects like Bring Your Own Key (BYOK) support, model routing rules, and the Dependency Injection (DI) container. We are not touching the existing `document.py` yet, but rather building the surrounding infrastructure that will eventually manipulate it. This cycle ensures that all subsequent development relies on strictly validated data structures, preventing runtime errors and enforcing the project's strict architectural boundaries from day one. The deliverables of this cycle will act as the contract between the application's business logic and its external dependencies.

This cycle is crucial for fulfilling the non-functional requirements related to security and configuration flexibility. By defining `AppConfig` and `ModelRoutingRules` as immutable Pydantic `BaseSettings`, we guarantee that sensitive API keys are loaded securely from environment variables and never accidentally serialized or logged. Furthermore, the introduction of a central `DIContainer` establishes the pattern for decoupling the application layer from concrete infrastructure implementations, a prerequisite for the rigorous, mock-free testing strategy required by the AC-CDD methodology. This cycle sets the stage for a scalable, maintainable, and secure enterprise application by defining the "grammar" the rest of the system will use to communicate.

## System Architecture

The architecture for this cycle is minimal but foundational. It introduces the configuration management layer and the Dependency Injection (DI) container. The DI container will act as the central registry for all application services and infrastructure adapters. At this stage, we are purely defining the structure; concrete implementations of external services (like the actual OpenRouter client) will come in later cycles. We define abstract protocols (`typing.Protocol`) to represent the capabilities the application needs, ensuring the application layer remains completely oblivious to specific technologies or vendors. This architecture guarantees strict separation of concerns, allowing business logic to be tested in complete isolation. The configuration layer utilizes Pydantic `BaseSettings` to parse environment variables, enforcing type safety and providing clear error messages if required configurations are missing or invalid upon application startup.

```text
matome/
├── src/
│   ├── **domain_models/**
│   │   ├── __init__.py
│   │   ├── document.py
│   │   ├── exceptions.py
│   │   ├── graph_state.py
│   │   ├── pivot.py
│   │   ├── **config.py**          (NEW)
│   ├── **interfaces/**
│   │   ├── **__init__.py**        (NEW)
│   │   ├── **llm_protocol.py**    (NEW)
│   ├── **application/**
│   │   ├── **__init__.py**        (NEW)
│   │   ├── **di_container.py**    (NEW)
```

## Design Architecture

This cycle focuses entirely on data structures and structural patterns. We are designing the foundational Pydantic models and the DI registry.

### 1. `src/domain_models/config.py`
This module contains the core configuration models for the application.
*   **`ModelRoutingRules`**: A Pydantic `BaseModel` that defines which LLM/VLM should be used for specific tasks. It should have fields like `text_fast_model` (defaulting to a fast, cheap model), `text_reasoning_model` (for complex tasks), and `multimodal_model`. It must strictly forbid extra fields (`model_config = ConfigDict(extra="forbid")`).
*   **`AppConfig`**: A Pydantic `BaseSettings` class. This is the root configuration object. It must read from environment variables. Crucially, it must include an `openrouter_api_key` field typed as `pydantic.SecretStr` to prevent accidental logging of the key. It should also embed the `ModelRoutingRules` as a nested model. To support multi-tenancy natively, it must include a `tenant_id` field. It must use `SettingsConfigDict(env_file=".env", extra="forbid")`.

**Invariants and Constraints:** The `AppConfig` must fail fast upon instantiation if required environment variables (like the API key or `tenant_id`) are missing, unless explicitly running in a designated "Mock Mode" for testing. The `ModelRoutingRules` ensure that the application always has a default model defined for every required capability, preventing runtime errors during routing. Including `tenant_id` in the core config ensures data is naturally isolated across tenants.

### 2. `src/interfaces/llm_protocol.py`
This module defines the abstract interface for the AI engine.
*   **`LLMProtocol`**: A `typing.Protocol` class. It defines the required capabilities of an LLM provider without specifying the implementation (e.g., OpenRouter, local Llama). It must define an asynchronous method, for example: `async def generate_text(self, prompt: str, model: str) -> str: ...`. This acts as the contract that the application layer will rely upon.

### 3. `src/application/di_container.py`
This module is the heart of the application's architectural decoupling.
*   **`DIContainer`**: A class responsible for registering and resolving dependencies. It should hold internal dictionaries (e.g., `_factories: dict[type, Callable]`, `_singletons: dict[type, Any]`).
*   It must implement a `register_singleton(interface: type, instance: Any)` method and a `resolve(interface: type) -> Any` method.
*   **Thread Safety:** The container's mutable state (the dictionaries) MUST be protected by a `threading.Lock()` to ensure thread safety if multiple asynchronous tasks attempt to register or resolve dependencies concurrently.
*   **Circular Dependency Detection:** The `resolve` method MUST track currently resolving interfaces using a `set[type]` (e.g., `_resolving`) to detect and raise a `RuntimeError` if a circular dependency is encountered, preventing stack overflows.

## Implementation Approach

1.  **Create `src/domain_models/config.py`**: Start by defining the `ModelRoutingRules` Pydantic model with its default values for different task types. Then, define the `AppConfig` inheriting from `pydantic_settings.BaseSettings`. Ensure `openrouter_api_key` is a `SecretStr` and that both models forbid extra fields.
2.  **Create `src/interfaces/llm_protocol.py`**: Define the abstract `LLMProtocol` class inheriting from `typing.Protocol`. Define the method signatures required for basic text generation. Ensure no concrete implementation details (like HTTP clients) leak into this file.
3.  **Create `src/application/di_container.py`**: Implement the `DIContainer` class. Initialize the internal dictionaries and the `threading.Lock()`. Implement the `register_singleton` and `resolve` methods.
4.  **Implement Thread Safety and Circular Dependency Logic**: Inside the `resolve` method of the `DIContainer`, add the logic to acquire the lock before accessing the internal dictionaries. Add the `_resolving` set logic: before resolving a dependency, check if it's in the set. If it is, raise a `RuntimeError("Circular dependency detected")`. If not, add it to the set, resolve the dependency, and finally, remove it from the set within a `finally` block to ensure it's always cleaned up.
5.  **Type Hinting Refinement**: Ensure all new files are strictly typed. When writing tests that resolve abstract protocols from the `DIContainer`, use the `# type: ignore[type-abstract]` comment to suppress Mypy's strict checking errors regarding abstract classes, as the container will return a concrete implementation at runtime.

## Test Strategy

The testing strategy for Cycle 01 focuses heavily on unit testing the structural integrity and validation rules of the new configuration and DI components. We must strictly adhere to the anti-mocking policy, avoiding `unittest.mock` and instead using real validation logic and simple custom classes.

**Unit Testing Approach (Minimum 300 words):**
We will thoroughly test the Pydantic models in `src/domain_models/config.py`. For `AppConfig`, we will use `pytest.MonkeyPatch` to simulate different environment variable states. We will test that instantiating `AppConfig` without the required `OPENROUTER_API_KEY` environment variable correctly raises a `pydantic.ValidationError`. We will also test that providing invalid configuration values (e.g., an empty string for a required model name in `ModelRoutingRules`) triggers the appropriate validation errors. The `SecretStr` typing of the API key must be verified to ensure the actual value is not exposed in the string representation of the config object. We will also verify that instantiating these models with undefined extra fields raises an error, confirming the `extra="forbid"` configuration is active.

For `src/application/di_container.py`, we will create a dedicated test suite. We will define dummy protocols and dummy concrete classes within the test file itself. We will test `register_singleton` and `resolve` to ensure a registered instance is correctly returned. Crucially, we will write a specific test to trigger a circular dependency. We will create two dummy classes that depend on each other and attempt to resolve them through the container, verifying that the container explicitly raises the expected `RuntimeError` regarding circular dependencies, proving the `_resolving` set logic works correctly. We will also test thread safety by launching multiple threads that concurrently attempt to register and resolve dependencies, ensuring no race conditions corrupt the internal state dictionaries.

**Integration Testing Approach (Minimum 300 words):**
While Cycle 01 primarily focuses on unit-level structures, we must perform integration testing to ensure these isolated components function together as intended. The primary integration point in this cycle is the interaction between the `AppConfig` and the `DIContainer`. We will write tests that instantiate a valid `AppConfig` using `MonkeyPatch` to provide simulated environment variables. We will then register this configuration instance as a singleton within the `DIContainer` under the `AppConfig` type.

Following registration, we will attempt to resolve the `AppConfig` back out of the container. The integration test must assert that the resolved object is identically the same instance (using the `is` operator) as the one initially registered. Furthermore, we will simulate a "Mock Mode" application startup scenario. We will define a `DummyLLMService` that implements the `LLMProtocol`. We will register this dummy service in the `DIContainer`. The test will then assert that resolving `LLMProtocol` from the container successfully returns the `DummyLLMService` instance. This verifies that the container correctly maps abstract interfaces to concrete implementations, laying the groundwork for how the application will substitute real services with test doubles in subsequent cycles or CI environments without relying on `unittest.mock`. This integration test proves the architectural scaffolding is robust and capable of supporting the decoupled design mandated by the AC-CDD methodology.