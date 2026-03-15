# CYCLE 02: LLM Interface & OpenRouter Integration - UAT Plan

## Summary
The User Acceptance Testing (UAT) for Cycle 02 verifies the critical communication layer between the `matome` system and external AI models via OpenRouter. This cycle focuses on the resilience, configuration, and abstraction of the `LLMProtocol` implementation (`OpenRouterClient`). The UAT scenarios are designed to ensure the system can reliably connect to external AI services, gracefully handle network instability (timeouts, bad gateways), and intelligently fall back to alternative models when primary options fail. This testing is crucial because the entire application's functionality hinges on stable and performant AI interactions.

As with Cycle 01, these tests are primarily developer-facing but are essential for proving the architectural robustness mandated by the system design objectives. We will use executable Marimo notebooks to demonstrate these behaviors, explicitly utilizing the "Mock Mode" and custom HTTP transports (`MockHttpxTransport`) to simulate complex network conditions deterministically without relying on actual, potentially flaky, external APIs or incurring unnecessary costs during testing.

## Test Scenarios

### Scenario ID: UAT-02-01
**Priority:** High
**Title:** Successful LLM Text Generation
**Description:** This scenario verifies the "happy path" of the `OpenRouterClient`. It ensures that given a valid prompt and model configuration, the client successfully formats the request according to the OpenRouter API specification, sends it asynchronously, parses the successful JSON response, and extracts the generated text correctly.

### Scenario ID: UAT-02-02
**Priority:** High
**Title:** Network Resilience: Retries on Transient Errors
**Description:** This scenario tests the system's fault tolerance against temporary network issues. It verifies that the `OpenRouterClient` automatically retries requests when encountering transient errors (like 502 Bad Gateway or connection timeouts) before ultimately failing. It ensures the application doesn't crash on the first sign of network instability.

### Scenario ID: UAT-02-03
**Priority:** High
**Title:** High Availability: Automatic Model Fallback
**Description:** This scenario validates the system's ability to maintain service availability even when specific AI models become unresponsive. It ensures that if requests to the primary configured model consistently fail (after retries), the client intelligently switches to a designated fallback model defined in the `AppConfig` to complete the request.

## Behavior Definitions

### UAT-02-01: Successful LLM Text Generation
**GIVEN** an initialized `OpenRouterClient` configured with a valid API key and a `MockHttpxTransport` set to return a `200 OK` response containing a standard OpenRouter JSON payload (e.g., `{"choices": [{"message": {"content": "Hello, world!"}}]}`).
**WHEN** the application calls the `generate_text` method on the client with the prompt "Say hello".
**THEN** the client must successfully execute the asynchronous request.
**AND** it must correctly parse the JSON response.
**AND** it must return the exact string `"Hello, world!"` without raising any exceptions.

### UAT-02-02: Network Resilience: Retries on Transient Errors
**GIVEN** an initialized `OpenRouterClient` configured with a `MockHttpxTransport`.
**AND GIVEN** the transport is configured to simulate a sequence of network failures: first raising an `httpx.ConnectTimeout`, then returning a `502 Bad Gateway` status code, and finally returning a successful `200 OK` response with the text `"Recovered!"`.
**WHEN** the application calls the `generate_text` method.
**THEN** the client must automatically catch the initial `TimeoutException` and `HTTPStatusError`.
**AND** it must execute exactly two retries (verifiable via a call counter on the mock transport).
**AND** it must eventually succeed on the third attempt, returning the string `"Recovered!"` without exposing the transient errors to the calling application layer.

### UAT-02-03: High Availability: Automatic Model Fallback
**GIVEN** an `AppConfig` defining a primary model (e.g., `claude-3-opus`) and a fallback model (e.g., `gpt-4o-mini`).
**AND GIVEN** an initialized `OpenRouterClient` using this config, paired with a `MockHttpxTransport`.
**AND GIVEN** the transport is configured to consistently raise an `httpx.ConnectTimeout` whenever the requested model is the primary model (`claude-3-opus`), but return a successful `200 OK` response with the text `"Fallback used"` when the requested model is the fallback model (`gpt-4o-mini`).
**WHEN** the application calls the `generate_text` method requesting the primary model.
**THEN** the client must exhaust its retries for the primary model.
**AND** instead of raising a final exception to the application, it must automatically catch the failure.
**AND** it must seamlessly initiate a new request using the configured fallback model (`gpt-4o-mini`).
**AND** it must successfully return the string `"Fallback used"`, ensuring the application logic completes despite the primary model's unavailability.