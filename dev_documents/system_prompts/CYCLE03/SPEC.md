# CYCLE 03: Document Ingestion & Chunking Pipeline

## Summary
With the core configuration and LLM infrastructure established in previous cycles, Cycle 03 focuses on the first critical domain workflow: Document Ingestion and Semantic Chunking. This cycle implements the pipeline that transforms raw, unstructured text into the highly structured, mathematically rigorous `SemanticChunk` objects defined in `src/domain_models/document.py`. This is the foundational step for the entire `matome` system, as all subsequent features—RAPTOR tree generation, semantic zooming, and Pivot KJ—depend entirely on the quality and density of these initial chunks.

We will build the `IngestionPipeline` service, orchestrating text parsing, intelligent chunking algorithms, and initial entity extraction using the `LLMProtocol`. Crucially, we will implement a semantic chunking strategy that goes beyond simple character limits, utilizing cosine similarity between adjacent sentences to divide text at logical proposition boundaries, as specified in the PRD (FR-1.2). We must also ensure that the generated embeddings strictly adhere to the dimensional constraints defined in the `SemanticChunk` Pydantic model. This cycle bridges the gap between raw data and the pure domain models, ensuring the resulting objects are pristine and ready for complex AI operations.

## System Architecture

The architecture for Cycle 03 sits primarily within the Application Layer (`src/application/`). We will create the `IngestionPipeline` class, which acts as the orchestrator for this phase. It will depend on three key protocols injected via the `DIContainer`: `LLMProtocol` (for entity extraction and potential semantic chunking assistance), an `EmbeddingProtocol` (to generate vector representations of text), and a `TextParserProtocol` (to handle different file formats, though we will focus initially on raw text for simplicity). The pipeline's output will be a list of instantiated, fully validated `SemanticChunk` domain models.

```text
matome/
├── src/
│   ├── domain_models/
│   │   ├── document.py        (Existing: SemanticChunk, ChunkMetadata)
│   ├── interfaces/
│   │   ├── llm_protocol.py    (Existing)
│   │   ├── **embedding_protocol.py** (NEW)
│   │   ├── **text_parser_protocol.py** (NEW)
│   ├── **application/**
│   │   ├── **ingestion.py**       (NEW: IngestionPipeline)
│   ├── infrastructure/
│   │   ├── openrouter.py      (Existing)
│   │   ├── **sentence_transformers.py** (NEW: Mockable Embedding)
```

## Design Architecture

This cycle focuses on the data transformation logic within the Application Layer, ensuring the outputs strictly conform to the `domain_models`.

### 1. `src/interfaces/embedding_protocol.py`
*   **`EmbeddingProtocol`**: A `typing.Protocol` defining the contract for generating vector embeddings. It must include an asynchronous method: `async def embed_text(self, text: str) -> list[float]: ...`. This abstraction allows us to swap between different embedding models (e.g., OpenAI's `text-embedding-3-small`, HuggingFace local models, or mock implementations for testing) without altering the core chunking logic.

### 2. `src/interfaces/text_parser_protocol.py`
*   **`TextParserProtocol`**: A `typing.Protocol` for extracting raw string content from various document formats (PDF, Markdown, etc.). It must include a method: `def parse(self, file_content: bytes, filename: str) -> str: ...`. For Cycle 03, we will implement a basic `PlainTextParser` to satisfy this, focusing on the chunking logic rather than complex file parsing (which can be added later).

### 3. `src/application/ingestion.py`
*   **`IngestionPipeline`**: The core application service for this cycle.
    *   **Dependencies**: Requires `LLMProtocol`, `EmbeddingProtocol`, and `TextParserProtocol` injected via `__init__`.
    *   **`process_document(file_content: bytes, filename: str) -> list[SemanticChunk]`**: The main orchestration method.
        1.  **Parse**: Use `TextParserProtocol` to get raw text.
        2.  **Chunk**: Implement a semantic chunking algorithm. This could involve using a lightweight NLP library (like `spacy` in the infrastructure layer, hidden behind an interface) to split text into sentences, calculate embeddings for each sentence (using `EmbeddingProtocol`), and group sentences where the cosine similarity remains high.
        3.  **Embed**: Generate a final embedding for each chunk.
        4.  **Extract Entities**: Concurrently (using `asyncio.gather`) call the `LLMProtocol` for each chunk with a prompt requesting entity extraction (e.g., "Extract proper nouns, key actors, and core concepts from this text: ...").
        5.  **Instantiate Domain Models**: For each processed chunk, create a `ChunkMetadata` object (populated with extracted entities and the source filename) and a `SemanticChunk` object.
    *   **Constraint Enforcement**: The pipeline must rely on the strict validation built into `SemanticChunk` (e.g., embedding dimensionality) to ensure invalid data never leaves the pipeline.

## Implementation Approach

1.  **Define New Protocols**: Create `src/interfaces/embedding_protocol.py` and `text_parser_protocol.py`. Ensure they are pure abstract interfaces (`typing.Protocol`).
2.  **Create Dummy Implementations**: In `src/infrastructure/test_services.py`, create a `DummyEmbeddingService` that returns a fixed-length list of random floats (e.g., `[0.1] * 384`), ensuring the dimension matches a valid dimension in `SemanticChunk`. Create a `PlainTextParser` that simply decodes bytes to strings.
3.  **Develop `IngestionPipeline`**: Create `src/application/ingestion.py`. Define the class and inject the protocols. Implement the `process_document` method.
4.  **Implement Semantic Chunking Logic**: Inside `process_document`, start with a simpler, length-based chunking strategy if semantic chunking is too complex for the initial iteration, but design the method signature to allow swapping it later. For a robust approach, use `spacy` (added to dev dependencies) to split into sentences, embed them, and group them based on similarity thresholds.
5.  **Integrate LLM Entity Extraction**: Write an asynchronous helper method within `IngestionPipeline` that constructs a prompt, calls `llm_service.generate_text`, parses the resulting string (expecting a comma-separated list or JSON array of entities), and returns a `list[str]`.
6.  **Construct Pydantic Models**: Ensure the final step of `process_document` rigorously uses the `SemanticChunk` and `ChunkMetadata` constructors. Any validation error raised here indicates a bug in the pipeline's logic that must be fixed.

## Test Strategy

The testing strategy for Cycle 03 must rigorously verify the data transformation pipeline without relying on external APIs or slow, heavy machine learning models. We will utilize the Dependency Injection container and the dummy services created in Cycle 02 and this cycle.

**Unit Testing Approach (Minimum 300 words):**
We will focus unit tests on the `IngestionPipeline` class in `src/application/ingestion.py`. We will inject the `DummyLLMService`, `DummyEmbeddingService`, and `PlainTextParser` (from `src/infrastructure/test_services.py`) into the pipeline.

First, we will test the basic chunking and instantiation logic. We will provide a sample raw text string (e.g., several paragraphs) to the `process_document` method. We will assert that the method returns a `list[SemanticChunk]`. We will iterate through this list and assert that every object is indeed an instance of `SemanticChunk` and that its internal `metadata` is an instance of `ChunkMetadata`. We will verify that the original text has been reasonably divided according to the implemented chunking algorithm (even if it's a simple length-based fallback for now).

Next, we must verify the integration of the injected protocols. We will configure the `DummyEmbeddingService` to always return an embedding of dimension 384. We will assert that every `SemanticChunk` returned by the pipeline has an `embedding` list of exactly length 384, confirming the pipeline correctly utilized the service and that the domain model validation passed.

Crucially, we will test the entity extraction logic. We will configure the `DummyLLMService` to return a specific, recognizable string when prompted for entities (e.g., `["EntityA", "EntityB"]`). We will assert that the `extracted_entities` list within the `ChunkMetadata` of the resulting chunks exactly matches the dummy output. This proves the pipeline is correctly orchestrating the asynchronous calls to the `LLMProtocol` and successfully mapping the results into the strict Pydantic structures.

Finally, we will test error handling and edge cases. What happens if the `LLMProtocol` raises an `LLMConnectionError` during entity extraction for a specific chunk? The pipeline should either retry, gracefully leave the entity list empty, or fail the entire document depending on the desired strictness, but it must not crash the application ungracefully. We will use a custom `FailingLLMService` to simulate this and assert the expected behavior.

**Integration Testing Approach (Minimum 300 words):**
The integration tests for Cycle 03 will verify the pipeline's behavior when wired into the `DIContainer` and ensure it respects the constraints of the `domain_models`.

We will write an integration test that bootstraps the `DIContainer`, explicitly registering the `DummyLLMService`, `DummyEmbeddingService`, and `PlainTextParser` against their respective protocols to simulate a "Mock Mode" execution environment. We will then register the `IngestionPipeline` itself.

The test will resolve the `IngestionPipeline` from the container. This verifies that all dependencies are correctly wired and that no circular dependencies exist. We will then call `process_document` with a substantial block of text (e.g., a multi-page Markdown document loaded from a test fixture file).

The primary assertion will focus on the final output against the domain model invariants. We will not just check that a list is returned; we will assert that the resulting chunks are valid according to the `DocumentValidator` defined in `src/domain_models/document.py` (which we will introduce or use if it exists). We will explicitly call `DocumentValidator.validate_embedding_consistency(chunks)` to ensure the pipeline hasn't accidentally mixed embedding models or produced chunks with varying dimensions.

Furthermore, we will intentionally configure the `DummyEmbeddingService` to return an invalid dimension (e.g., length 3, which is not in the allowed set {256, 384, ...} defined in `SemanticChunk`). We will then run the pipeline and assert that a `pydantic.ValidationError` is immediately raised during the instantiation of the `SemanticChunk` models within the pipeline. This negative test crucially proves that the strict Pydantic validation rules are actively protecting the domain from malformed data originating in the application or infrastructure layers. This confirms the AC-CDD principle that domain models are the ultimate source of truth and validation.