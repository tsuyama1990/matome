# CYCLE 06: Pivot KJ Engine & Export Generation

## Summary
Cycle 06 represents the culmination of the `matome` platform's capabilities, implementing the "Pivot KJ for Requirements Definition and Knowledge Reconstruction" feature (PRD FR-3.5). While previous cycles focused on ingesting information and facilitating learning via the established table of contents (the "As-Is" structure), this cycle empowers the user to dynamically reorganize the entire knowledge graph based on new, multi-dimensional axes (e.g., SWOT, Data Flow, Actors). This is the transition from knowledge *consumption* to knowledge *production*.

We will develop the `PivotEngine`, an application service that takes the existing `EnrichedDocument` and a chosen `PivotAxis`, queries the Vector Database (or a local equivalent for testing) to find relevant chunks, and uses a reasoning LLM to deduce the new structural relationships (the "To-Be" structure). Finally, we will implement an `ExportService` that can translate this newly formed graph into standardized formats like Markdown PRDs or PlantUML/Mermaid diagrams. This cycle proves the system's ultimate value proposition: transforming massive, static documents into flexible, actionable insights.

## System Architecture

The architecture for Cycle 06 heavily involves the Application Layer orchestrating both the Vector DB and the LLM. The `PivotEngine` takes the user's current state and a target axis. It interacts with the `VectorDBProtocol` (to find chunks strongly related to the new axis) and the `LLMProtocol` (to analyze these chunks and propose a new logical grouping). The output is a `PivotState` domain model (defined in `src/domain_models/pivot.py`) representing the reconstructed graph. The `ExportService` then acts upon this `PivotState` to generate external artifacts.

```text
matome/
├── src/
│   ├── domain_models/
│   │   ├── document.py        (Existing)
│   │   ├── **pivot.py**           (Existing, to be refined: PivotState, PivotNode)
│   ├── interfaces/
│   │   ├── llm_protocol.py    (Existing)
│   │   ├── **vector_db.py**       (NEW: VectorDBProtocol)
│   ├── **application/**
│   │   ├── **pivot_engine.py**    (NEW: Pivot logic)
│   │   ├── **export_service.py**  (NEW: Markdown/UML generation)
│   ├── infrastructure/
│   │   ├── **pinecone_client.py** (NEW: Concrete Vector DB)
```

## Design Architecture

This cycle focuses on complex query orchestration and data transformation into new schemas.

### 1. `src/interfaces/vector_db.py`
*   **`VectorDBProtocol`**: A `typing.Protocol` defining the contract for similarity search.
    *   `async def upsert(self, chunks: list[SemanticChunk]) -> None: ...`
    *   `async def search(self, query_embedding: list[float], top_k: int, filter_metadata: dict | None = None) -> list[SemanticChunk]: ...`
    This abstraction allows us to use an in-memory mock for tests and Pinecone/Qdrant in production.

### 2. `src/domain_models/pivot.py` (Refinement)
*   **`PivotNode`**: A Pydantic model representing a node in the *reconstructed* graph. It differs from `RaptorNode` as it represents a concept on a new axis (e.g., "Strength" in a SWOT analysis). It contains `node_id`, `label` (e.g., "High Brand Value"), `summary`, and `source_chunk_ids` (maintaining traceability to the original text).
*   **`PivotState`**: The overall state of the newly formed graph. It contains `original_document_id`, `axis_name` (e.g., "SWOT"), and `nodes: list[PivotNode]`.

### 3. `src/application/pivot_engine.py`
*   **`PivotEngine`**: The core service for knowledge reconstruction.
    *   **Dependencies**: Requires `LLMProtocol`, `VectorDBProtocol`, and `EmbeddingProtocol`.
    *   **`execute_pivot(document: EnrichedDocument, axis: str) -> PivotState`**: The main orchestration method.
        1.  **Define Axis Prompts**: Based on the `axis` (e.g., "System Actors"), retrieve predefined sub-categories or reasoning prompts.
        2.  **Semantic Search & Metadata Filtering (CRITICAL)**: Use the `EmbeddingProtocol` to embed the axis names (e.g., embed the word "Security Constraint"). Query the `VectorDBProtocol` to find `SemanticChunk`s highly relevant to this axis. CRUCIALLY, the search MUST utilize the pre-calculated metadata tags generated in Cycle 03 (e.g., filtering `filter_metadata={"time_axis": "Future"}`) to drastically reduce the number of chunks sent to the LLM context window.
        3.  **LLM Reasoning**: Send the filtered and retrieved chunks to the `LLMProtocol` with a complex reasoning prompt (e.g., "Analyze these filtered chunks. Identify all system actors. For each actor, summarize their responsibilities and list the IDs of the source chunks providing this evidence").
        4.  **Construct State**: Parse the LLM's structured output (preferably JSON) to instantiate the `PivotNode` and `PivotState` Pydantic models.

### 4. `src/application/export_service.py`
*   **`ExportService`**: Converts `PivotState` into external formats.
    *   **`generate_markdown(state: PivotState) -> str`**: Formats the pivot nodes into a readable Markdown report.
    *   **`generate_mermaid(state: PivotState) -> str`**: (Optional/Advanced) Uses the LLM to deduce relationships between `PivotNode`s (e.g., data flows between "Actors") and outputs Mermaid diagram syntax.

## Implementation Approach

1.  **Define `VectorDBProtocol`**: Create `src/interfaces/vector_db.py`.
2.  **Create Dummy Vector DB**: In `src/infrastructure/test_services.py`, create a `DummyVectorDB` that stores chunks in a simple list and returns random chunks for `search`.
3.  **Refine Pivot Models**: Ensure `src/domain_models/pivot.py` models are strictly typed and forbid extra fields.
4.  **Develop `PivotEngine`**: Create `src/application/pivot_engine.py`. Inject the required protocols.
5.  **Implement `execute_pivot`**: Start with defining the specific `filter_metadata` query based on the requested `axis`. Execute the `VectorDBProtocol.search` with this filter. Pass the filtered subset of chunks to the LLM and ask it to categorize them. Parse the result into `PivotNode`s. Ensure the LLM prompt explicitly demands traceability (returning the original chunk IDs).
6.  **Develop `ExportService`**: Implement `generate_markdown` to iterate through the `PivotState` and create a formatted string.
7.  **Integrate with DI**: Register all new services and dummies in the `DIContainer`.

## Test Strategy

Testing Cycle 06 requires sophisticated mocking of both the Vector Database and the LLM to verify complex data restructuring logic.

**Unit Testing Approach (Minimum 300 words):**
We will focus unit testing heavily on the `PivotEngine` using the `DIContainer` and dummy services. We will inject the `DummyLLMService`, `DummyEmbeddingService`, and the newly created `DummyVectorDB`.

First, we will test the orchestration of `execute_pivot`. We will provide a mock `EnrichedDocument` containing several `SemanticChunk` objects. We will configure the `DummyVectorDB` to return a specific subset of these chunks when searched. We will then configure the `DummyLLMService` to return a strictly formatted JSON string representing the restructured categorization (e.g., `{"categories": [{"name": "Actor A", "chunk_ids": ["chunk1", "chunk2"]}]}`).

We will call `execute_pivot(document, "Actors")`. We will assert that the `PivotEngine` successfully orchestrates the flow: it queries the Vector DB (verifiable if we use a spy), it calls the LLM with the retrieved chunks, and crucially, it successfully parses the mock JSON output into valid `PivotNode` and `PivotState` Pydantic models. We will specifically assert the traceability requirement: that the `source_chunk_ids` in the resulting `PivotNode` correctly correspond to the original chunks from the mock document. This proves the complex transformation logic works.

Next, we will unit test the `ExportService` in complete isolation. We will manually construct a valid `PivotState` object (without involving the engine or LLMs). We will pass this state to `generate_markdown`. We will assert that the resulting string contains the expected Markdown formatting (headers for node labels, bullet points for summaries) and correctly represents the data within the `PivotState` object.

**Integration Testing Approach (Minimum 300 words):**
The integration test for Cycle 06 will simulate the complete user journey from a standard document view to a restructured "Pivot" view, executing entirely in "Mock Mode".

We will configure the `DIContainer` with all necessary dummy services (LLM, Embedding, VectorDB). We will initialize a dummy `EnrichedDocument`.

The test will perform the following sequence:
1.  **Ingest to Vector DB**: Simulate the end of Cycle 03 by calling `VectorDBProtocol.upsert` with the document's chunks.
2.  **Execute Pivot**: Call `PivotEngine.execute_pivot` with a specific axis (e.g., "SWOT Analysis").
3.  **Validate Pivot State**: Assert that the returned object is a valid `PivotState`. Assert that the `axis_name` matches the request. Iterate through the `PivotNode`s and assert that their internal structure (labels, summaries, source IDs) is valid according to the Pydantic constraints.
4.  **Execute Export**: Pass the resulting `PivotState` to `ExportService.generate_markdown`.
5.  **Validate Export**: Assert that the output is a non-empty string and contains keywords expected from the requested axis (e.g., "Strengths", "Weaknesses").

Furthermore, we must test the system's resilience to bad LLM outputs. We will configure the `DummyLLMService` to return malformed JSON or unstructured text during the `execute_pivot` call. We will assert that the `PivotEngine` catches the parsing error gracefully, potentially retries (if retry logic is implemented), and ultimately raises a clear domain exception (e.g., `PivotGenerationError`) rather than crashing the application or returning invalid state objects. This confirms the system remains robust even when the AI fails to follow instructions.