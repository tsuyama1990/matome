# CYCLE 03: Document Ingestion & Chunking Pipeline - UAT Plan

## Summary
The User Acceptance Testing (UAT) for Cycle 03 verifies the crucial transformation of raw user documents into the structured data format (`SemanticChunk`) required by the `matome` system. This cycle is fundamentally about data ingestion and the first stage of AI processing. The UAT scenarios ensure that the system can handle realistic document text, divide it logically (avoiding abrupt mid-sentence cuts), and successfully orchestrate external AI models to extract meaningful metadata (entities) and vector representations (embeddings).

This UAT will be implemented in the `tutorials/UAT_AND_TUTORIAL.py` Marimo notebook. While the underlying mechanics are complex (involving NLP and LLM calls), the UAT will focus on the observable output: ensuring that a given document is broken down into a complete, consistent, and semantically coherent list of chunks. We will heavily utilize the "Mock Mode" to guarantee these tests can run deterministically in any environment without requiring actual API keys, proving the pipeline's logic is sound regardless of the specific AI models used.

## Test Scenarios

### Scenario ID: UAT-03-01
**Priority:** High
**Title:** End-to-End Document Ingestion (Mock Mode)
**Description:** This scenario verifies the entire ingestion pipeline from raw text to a list of validated `SemanticChunk` objects. It ensures that the application service correctly coordinates the text parser, the chunking algorithm, the embedding service, and the LLM entity extractor. This is the primary "happy path" test for the ingestion workflow.

### Scenario ID: UAT-03-02
**Priority:** High
**Title:** Semantic Boundary Adherence
**Description:** This scenario tests the intelligence of the chunking algorithm. It ensures that the system does not simply split text by a rigid character limit, which would destroy context (the "Lost-in-the-Middle" problem). It verifies that chunks generally respect sentence boundaries and logical paragraph breaks.

### Scenario ID: UAT-03-03
**Priority:** Medium
**Title:** Strict Domain Validation Enforcement
**Description:** This scenario validates that the ingestion pipeline strictly adheres to the constraints defined in the `src/domain_models/document.py` Pydantic models. It ensures that if any infrastructure component (like a faulty embedding model) returns invalid data (e.g., wrong dimensionality), the system immediately halts and raises a validation error, preventing corrupt data from entering the core system.

## Behavior Definitions

### UAT-03-01: End-to-End Document Ingestion (Mock Mode)
**GIVEN** an application configured in "Mock Mode", with a `DummyLLMService` (returning fixed entities like `["MockEntityA"]`) and a `DummyEmbeddingService` (returning fixed-size vectors, e.g., dimension 384) registered in the `DIContainer`.
**AND GIVEN** a sample raw text document containing multiple paragraphs (e.g., a short article about artificial intelligence).
**WHEN** the application's `IngestionPipeline` processes this document.
**THEN** the pipeline must execute successfully without errors.
**AND** it must return a list of `SemanticChunk` objects.
**AND** every chunk in the list must have a valid UUID.
**AND** every chunk must have an `embedding` vector of exactly length 384.
**AND** every chunk's `metadata` must contain the extracted entities `["MockEntityA"]`, proving the AI orchestration occurred.
**AND** every chunk's `metadata` must have the `time_axis` field populated (e.g., "Present"), verifying the pre-tagging requirement.

### UAT-03-02: Semantic Boundary Adherence
**GIVEN** an application configured with a basic sentence-aware chunking algorithm (even in Mock Mode).
**AND GIVEN** a specific test string containing a very long sentence followed by a short sentence, designed to exceed a naive character limit exactly in the middle of a word or phrase (e.g., "This is a very long sentence that discusses the complexities of natural language processing and how it relates to cognitive load theory. Here is another sentence.").
**WHEN** the `IngestionPipeline` processes this specific text.
**THEN** the resulting `SemanticChunk` objects must NOT contain a chunk that abruptly ends mid-word or mid-sentence (e.g., ending with "natural language proce").
**AND** the chunks should logically group the text, ideally keeping complete sentences intact within a single chunk, demonstrating that the system respects semantic boundaries over rigid character counts.

### UAT-03-03: Strict Domain Validation Enforcement
**GIVEN** an application where the `DIContainer` is intentionally misconfigured to inject a "FaultyEmbeddingService" that returns an embedding vector of an invalid length (e.g., length 3, which is not in the allowed set `{256, 384, 512, ...}` defined by the `SemanticChunk` Pydantic model).
**WHEN** the `IngestionPipeline` attempts to process any standard text document.
**THEN** the pipeline must NOT silently process the document or return partially formed data.
**AND** the application must immediately raise a `pydantic.ValidationError` explicitly citing the `embedding` dimension constraint.
**AND** this error must originate from the `SemanticChunk` constructor, proving that the domain model's invariants successfully caught and blocked the invalid infrastructure output before it could propagate further into the system.