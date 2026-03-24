# CYCLE 01: Core Domain Models & Configuration Foundation - UAT Plan

## Summary
The User Acceptance Testing (UAT) for Cycle 01 focuses on verifying the fundamental configuration and architectural plumbing of the `matome` system. Because this cycle primarily establishes internal structures (Pydantic models and the Dependency Injection container), the UAT will be developer-facing rather than end-user facing. However, it is critical to ensure these foundational elements behave exactly as specified, as they dictate the security and stability of the entire application. The UAT will be implemented as an executable Marimo notebook (`tutorials/UAT_AND_TUTORIAL.py`), which will serve as both a test suite and a tutorial on how the application manages its configuration and dependencies. This notebook must gracefully handle environments with or without actual API keys by utilizing the "Mock Mode" strategy mandated by the architecture.

This UAT will prove that the application strictly enforces configuration rules, preventing startup if required settings are missing or invalid, and securely handling sensitive credentials. It will also demonstrate the DI container's ability to map abstract protocols to concrete implementations, proving the system's modularity. By executing this Marimo notebook, we guarantee that the core scaffolding of `matome` is robust and ready to support the complex AI orchestrations planned for subsequent cycles.

## Test Scenarios

### Scenario ID: UAT-01-01
**Priority:** High
**Title:** Secure Application Configuration and Startup
**Description:** This scenario verifies that the application's core configuration (`AppConfig` and `ModelRoutingRules`) is loaded correctly from environment variables and strictly validated. It ensures that the system refuses to start (raises a validation error) if critical settings like the API key are missing or if invalid configuration values are provided. It also explicitly checks that sensitive fields are not exposed in plaintext representations.

### Scenario ID: UAT-01-02
**Priority:** High
**Title:** Dependency Injection and Protocol Resolution
**Description:** This scenario validates the core architectural pattern of the application: Dependency Injection. It proves that the `DIContainer` can successfully register both singleton instances and factory functions against abstract protocols (like `LLMProtocol`). It further verifies that the container correctly resolves these dependencies when requested, returning the appropriate concrete implementation, and properly handles circular dependency errors.

### Scenario ID: UAT-01-03
**Priority:** Medium
**Title:** Hybrid Environment "Mock Mode" Execution
**Description:** This scenario demonstrates the system's resilience in environments where external services (like OpenRouter) are unavailable or unconfigured, such as in CI pipelines. It verifies that the application can seamlessly fall back to a "Mock Mode" by registering deterministic, dummy implementations of core protocols (e.g., a `DummyLLMService`) within the DI container, allowing the application logic to execute without relying on external APIs.

## Behavior Definitions

### UAT-01-01: Secure Application Configuration and Startup
**GIVEN** an environment where the `OPENROUTER_API_KEY` environment variable is not set.
**WHEN** the application attempts to initialize the `AppConfig` Pydantic model.
**THEN** the initialization must immediately fail, raising a `pydantic.ValidationError` detailing the missing required field.

**GIVEN** an environment where the `OPENROUTER_API_KEY` is set to a valid string, but a required routing rule (e.g., `text_fast_model`) is set to an empty string.
**WHEN** the application attempts to initialize the `AppConfig` model.
**THEN** the initialization must fail, raising a `pydantic.ValidationError` indicating an invalid model name string.

**GIVEN** a correctly configured environment with a valid `OPENROUTER_API_KEY`.
**WHEN** the `AppConfig` model is successfully instantiated.
**THEN** printing or logging the `AppConfig` instance must display the API key as a masked `SecretStr` (e.g., `**********`), explicitly preventing the plaintext key from leaking into application logs or console output.

### UAT-01-02: Dependency Injection and Protocol Resolution
**GIVEN** an initialized `DIContainer` and a concrete class `DummyLLMService` that implements the `LLMProtocol`.
**WHEN** the `DummyLLMService` instance is registered as a singleton against the `LLMProtocol` type in the container.
**AND WHEN** the application logic subsequently resolves the `LLMProtocol` from the container.
**THEN** the container must return the exact `DummyLLMService` instance that was registered, verifying successful dependency injection.

**GIVEN** an initialized `DIContainer` and two classes, `ServiceA` and `ServiceB`, where `ServiceA`'s factory requires `ServiceB`, and `ServiceB`'s factory requires `ServiceA`.
**WHEN** both factories are registered in the container and the application attempts to resolve `ServiceA`.
**THEN** the container must immediately detect the circular dependency during resolution and explicitly raise a `RuntimeError("Circular dependency detected")`, preventing an infinite recursion stack overflow.

### UAT-01-03: Hybrid Environment "Mock Mode" Execution
**GIVEN** an environment explicitly configured to run in "Mock Mode" (e.g., an environment variable `MATOME_MOCK_MODE=true` is set).
**WHEN** the application bootstraps its `DIContainer`.
**THEN** the container must bypass registering real external service clients (like the OpenRouter client).
**AND** it must instead register deterministic test doubles (e.g., a `DummyLLMService` that always returns a fixed string) for all required protocols (e.g., `LLMProtocol`).
**AND WHEN** the application executes its core logic, resolving dependencies from the container.
**THEN** the execution must complete successfully without making any external network requests, relying entirely on the injected mock implementations.