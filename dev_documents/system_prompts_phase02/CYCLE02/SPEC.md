# CYCLE 02: LLM Interface & OpenRouter Integration

## Summary
Building upon the solid configuration and Dependency Injection foundation established in Cycle 01, Cycle 02 shifts focus to the system's external intelligence: the Large Language Models (LLMs). The core objective of this cycle is to implement a robust, reliable, and configurable communication layer with OpenRouter, which acts as the application's single gateway to various AI models (like Gemini, GPT-4o, and Claude). We will create the concrete infrastructure class that fulfills the `LLMProtocol` defined previously. This is a critical step because the entire `matome` value proposition—semantic chunking, RAPTOR tree generation, and dynamic user interactions—relies entirely on high-performance, fault-tolerant LLM calls. We must ensure this layer handles the inherent unreliability of network requests and third-party APIs gracefully, incorporating timeouts, retries, and fallback mechanisms as specified in the non-functional requirements.

This cycle strictly adheres to the architectural boundaries by placing all OpenRouter-specific logic within the `src/infrastructure/` directory. The rest of the application will remain oblivious to HTTP clients or specific API payloads, interacting only through the abstract `LLMProtocol`. We will utilize the modern, asynchronous `httpx` library for network communication to meet the low-latency and high-throughput requirements. Furthermore, we will implement the testing strategy for this layer without relying on standard mock objects, instead using custom `httpx` transports to simulate API responses and failures deterministically. This ensures the integration is rigorously tested for resilience before it is wired into the core business logic in subsequent cycles.

## System Architecture

This cycle focuses on the Infrastructure Layer, specifically the component responsible for external AI model communication. We will implement the `OpenRouterClient` which will be registered in the `DIContainer` established in Cycle 01 to satisfy the `LLMProtocol`. The client must utilize the `AppConfig` to securely access API keys and routing rules. It must use an asynchronous HTTP client (`httpx.AsyncClient`) to ensure non-blocking operations, critical for maintaining the high-performance UI requirements.

```text
matome/
├── src/
│   ├── domain_models/
│   │   └── config.py
│   ├── interfaces/
│   │   └── llm_protocol.py
│   ├── application/
│   │   └── di_container.py
│   ├── **infrastructure/**
│   │   ├── **__init__.py**        (NEW)
│   │   ├── **openrouter.py**      (NEW)
│   │   └── **test_services.py**   (NEW)
```

## Design Architecture

This cycle designs the concrete implementation of the AI communication layer, focusing on resilience, configuration injection, and abstract interface fulfillment.

### 1. `src/infrastructure/openrouter.py`
This module contains the concrete implementation of the `LLMProtocol`.
*   **`OpenRouterClient`**: A class that implements the `LLMProtocol`. It requires `AppConfig` to be injected upon instantiation to access the API key and base URL.
*   **Asynchronous Communication**: It must use `httpx.AsyncClient` for all network requests to OpenRouter. The client should be configured with appropriate timeouts (e.g., connection, read, write) to prevent the application from hanging indefinitely if the external API is unresponsive.
*   **Error Handling and Retries**: The `generate_text` method (and any other methods fulfilling the protocol) must robustly handle `httpx.RequestError` and `httpx.HTTPStatusError`. It should implement a retry mechanism (e.g., using the `tenacity` library) for transient errors (like 502 Bad Gateway or 429 Too Many Requests), but gracefully fail for permanent errors (like 401 Unauthorized) by raising a custom domain exception (defined in `src/domain_models/exceptions.py`).
*   **Model Fallback Logic**: If a request to the primary model specified in `ModelRoutingRules` repeatedly fails or times out, the client must automatically attempt the request using a designated fallback model (e.g., switching from a complex reasoning model to a faster, more reliable model if the former is unavailable).

### 2. `src/infrastructure/test_services.py`
This module contains deterministic test doubles for infrastructure components, adhering to the project's anti-mocking policy.
*   **`DummyLLMService`**: A simple class implementing `LLMProtocol` that returns predictable, hardcoded strings based on the input prompt. This is crucial for "Mock Mode" execution and unit testing application logic in later cycles without hitting the real OpenRouter API.
*   **`MockHttpxTransport`**: A custom class inheriting from `httpx.AsyncBaseTransport`. It intercepts all outbound requests from the `httpx.AsyncClient` used by the `OpenRouterClient` during testing. It allows tests to define exactly what HTTP response (status code, JSON body, or exception) should be returned for a specific request URL or payload, enabling rigorous testing of error handling and retry logic without making actual network calls.

## Implementation Approach

1.  **Define Domain Exceptions**: First, create `src/domain_models/exceptions.py` (if it doesn't exist) and define custom exceptions like `LLMConnectionError` and `LLMAuthenticationError` to map low-level HTTP errors to domain-specific concepts.
2.  **Implement `OpenRouterClient`**: Create `src/infrastructure/openrouter.py`. Define the `OpenRouterClient` class implementing `LLMProtocol`. Initialize it with `AppConfig`. Implement the `generate_text` method using `httpx.AsyncClient`.
3.  **Add Resilience (Tenacity)**: Decorate the `generate_text` method (or an internal helper method) with `@retry` from the `tenacity` library. Configure it to retry on specific `httpx` exceptions (e.g., `TimeoutException`, `ConnectError`) with an exponential backoff strategy, limiting the total number of retries.
4.  **Implement Fallback Logic**: Within the `generate_text` method, wrap the primary model request in a `try...except` block. If the retries are exhausted and a specific exception is raised, catch it, log a warning, and re-attempt the request using the fallback model defined in the configuration.
5.  **Create Test Doubles**: Implement the `DummyLLMService` and `MockHttpxTransport` in `src/infrastructure/test_services.py`. Ensure `MockHttpxTransport` can yield `httpx.Response` objects or raise specific `httpx` exceptions based on configuration provided by the test.

## Test Strategy

The testing strategy for Cycle 02 relies entirely on custom test transports and deterministic responses, strictly avoiding `unittest.mock.patch`. This ensures the network resilience logic is genuinely exercised.

**Unit Testing Approach (Minimum 300 words):**
We will thoroughly unit test the `OpenRouterClient` in isolation. To achieve this without external network calls or standard mocks, we will instantiate the `OpenRouterClient` but inject an `httpx.AsyncClient` configured with our custom `MockHttpxTransport` (defined in `src/infrastructure/test_services.py`).

First, we will test the successful "Happy Path." We will configure the `MockHttpxTransport` to return a 200 OK HTTP response with a valid JSON payload resembling an OpenRouter response. We will then call the `generate_text` method on the `OpenRouterClient` and assert that it correctly parses the JSON and returns the expected text string.

Next, we must aggressively test the error handling and retry logic. We will configure the `MockHttpxTransport` to simulate a transient network error by raising an `httpx.ConnectTimeout`. We will assert that the `OpenRouterClient` automatically retries the request the configured number of times (verifying this by tracking the number of times the transport's `handle_async_request` method was called). We will also configure the transport to simulate a permanent 401 Unauthorized error and assert that the client immediately raises our custom `LLMAuthenticationError` domain exception without retrying. Finally, we will test the fallback mechanism: we will configure the transport to consistently fail for the primary model, and assert that the client catches the final exception, successfully makes a request using the fallback model, and returns its result, ensuring the application remains resilient even when specific AI models are unavailable.

**Integration Testing Approach (Minimum 300 words):**
The integration testing for Cycle 02 focuses on wiring the new `OpenRouterClient` into the `DIContainer` established in Cycle 01 and verifying it interacts correctly with the `AppConfig`.

We will create an integration test that instantiates a real `AppConfig` (using `pytest.MonkeyPatch` to provide a valid, albeit perhaps fake, API key in the environment variables). We will then register the `OpenRouterClient` factory function within the `DIContainer`, ensuring it specifies that the `OpenRouterClient` requires the `AppConfig` dependency.

The test will then call `container.resolve(LLMProtocol)`. We will assert that the returned object is indeed an instance of `OpenRouterClient`. We will further inspect this instance to verify that its internal configuration (like the base URL and API key header) correctly matches the values provided by the injected `AppConfig`.

Finally, to demonstrate the system's "Mock Mode" capability, we will write a separate integration test where the container is configured to register the `DummyLLMService` (from `src/infrastructure/test_services.py`) instead of the real client. We will assert that resolving `LLMProtocol` returns the dummy service, and calling its `generate_text` method returns the expected hardcoded string. This proves the architecture successfully decouples the business logic from the concrete infrastructure, allowing for seamless substitution of real services with test doubles during automated testing or offline execution environments.