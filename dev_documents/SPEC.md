# Phase 2 Specifications: Infrastructure Adapters

This document details the exact requirements for implementing the Infrastructure layer (Cycle 02).
Based on the defined architecture, you will implement adapters that realize the interfaces defined in Cycle 01.

## Scope of Cycle 02

The scope for this phase is to implement two key infrastructure classes in `src/infrastructure/`:
1.  **OpenRouterGateway**: An implementation of `LLMProtocol` that talks to the OpenRouter API.
2.  **MockVectorDB**: A mock Vector Database adapter (for testing and local dev).

## 1. Domain Constraints & Design Architecture

### 1.1 OpenRouterGateway
The `OpenRouterGateway` must realize `src.interfaces.LLMProtocol`.
- **Initialization**: Must accept a `CredentialConfig` and `PipelineConfig` instance.
- **HTTP Client**: Must use `httpx.Client` or `requests.Session` to manage connections.
- **Endpoint**: Connect to `https://openrouter.ai/api/v1/chat/completions`.
- **Headers**: Must strictly include the `Authorization: Bearer <decrypted_key>` header.
- **Error Handling**: Must catch network exceptions, timeouts, and HTTP errors (4xx, 5xx), wrapping them in the domain's `LLMError`.
- **Timeouts & Retries**: Must implement the `timeout` and `retries` logic as specified in the protocol.

### 1.2 MockVectorDB
A simple in-memory vector database interface implementation for testing.
- **Initialization**: Simple initialization.
- **Methods**: Implement a basic storage and retrieval mechanism for `SemanticChunk` models.
- **Note**: A full `VectorDBProtocol` might not be defined in `interfaces.py` yet. If it's missing, you should define a minimal `VectorDBProtocol` in `src/interfaces.py` and implement it in `src/infrastructure/mock_vdb.py`.

## 2. Implementation Approach

1.  **Dependencies**: Add `httpx` or `requests` to `pyproject.toml` using `uv add httpx` (or `requests`).
2.  **Define Interfaces**: Check if `VectorDBProtocol` is in `src/interfaces.py`. If not, add it.
    - Example: `def store(self, chunks: list[SemanticChunk]) -> None`, `def search(self, query: str, top_k: int) -> list[SemanticChunk]`.
3.  **Implement Adapters**: Create `src/infrastructure/__init__.py`, `src/infrastructure/openrouter.py`, and `src/infrastructure/mock_vdb.py`.
4.  **TDD**: Write tests in `tests/unit/test_infrastructure.py` to ensure:
    - `OpenRouterGateway` correctly formats request headers.
    - `OpenRouterGateway` correctly raises `LLMError` on failure.
    - `MockVectorDB` can store and retrieve chunks correctly.

## 3. Strict Rules
- **No Direct Mocking in Business Logic**: While `MockVectorDB` is a mock, `OpenRouterGateway` must be fully functional.
- **Security**: NEVER print or log the API key. Use `get_decrypted_api_key()` right before the HTTP call.
