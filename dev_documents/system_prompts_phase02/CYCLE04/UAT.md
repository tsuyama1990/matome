# CYCLE 04: RAPTOR Tree Generation & Summarization - UAT Plan

## Summary
The User Acceptance Testing (UAT) for Cycle 04 validates the most crucial and complex backend processing step: the generation of the hierarchical RAPTOR summary tree. This cycle transforms the flat list of text chunks (from Cycle 03) into a navigable, multi-layered knowledge graph, directly addressing the "Cognitive Overload" problem identified in the PRD. The UAT scenarios ensure that the system can intelligently group related pieces of information (using mathematical clustering on embeddings) and generate highly dense, accurate summaries for these groups (using the Chain of Density LLM prompt).

This UAT will be implemented in the `tutorials/UAT_AND_TUTORIAL.py` Marimo notebook. Because actual clustering and LLM summarization are non-deterministic and computationally expensive, these tests will extensively utilize the "Mock Mode" architecture to ensure they run reliably, quickly, and without API costs in any environment. The focus is on proving the *orchestration* of these complex processes—verifying that the right data is grouped, the right prompts are sent to the AI, and the resulting tree structure is logically sound and strictly adheres to the domain schemas.

## Test Scenarios

### Scenario ID: UAT-04-01
**Priority:** High
**Title:** Hierarchical Tree Construction (Mock Mode)
**Description:** This scenario verifies the core orchestration of the `RaptorEngine`. It ensures that given a set of `SemanticChunk` objects, the engine successfully utilizes a clustering algorithm (or a deterministic mock version) to group them, and then concurrently orchestrates the `LLMProtocol` to generate summaries for each group, ultimately producing a valid list of `RaptorNode` objects.

### Scenario ID: UAT-04-02
**Priority:** High
**Title:** Chain of Density Prompt Generation
**Description:** This scenario specifically tests the "Information Super-Densification" requirement (FR-1.4). It verifies that the `RaptorEngine` correctly formats the prompts sent to the LLM when summarizing a cluster of chunks, explicitly instructing the AI to use an iterative densification process (e.g., "rewrite 3 times adding missing entities"). This ensures the resulting summaries will actually reduce cognitive load.

### Scenario ID: UAT-04-03
**Priority:** Medium
**Title:** Tree Relational Integrity and Schema Enforcement
**Description:** This scenario validates the structural integrity of the final output. It ensures that the generated `RaptorNode` objects correctly point back to their constituent `SemanticChunk` objects (no dangling pointers), and that the entire hierarchy is securely encapsulated within the strictly validated `EnrichedDocument` Pydantic model.

## Behavior Definitions

### UAT-04-01: Hierarchical Tree Construction (Mock Mode)
**GIVEN** an application configured in "Mock Mode", with a `DummyLLMService` (returning "Mock Summary") and a `MockClusterer` (deterministically grouping chunks into pairs) registered in the `DIContainer`.
**AND GIVEN** a predefined list of six valid `SemanticChunk` objects.
**WHEN** the application's `RaptorEngine` processes these chunks to build a tree.
**THEN** the engine must execute successfully without errors.
**AND** it must return a list of exactly three `RaptorNode` objects (since the 6 chunks were grouped into pairs).
**AND** every `RaptorNode` must have its `summarized_content` set to "Mock Summary".
**AND** every `RaptorNode` must have exactly two `children_ids` corresponding to the UUIDs of the original chunks it represents, proving the grouping logic functioned correctly.

### UAT-04-02: Chain of Density Prompt Generation
**GIVEN** an application configured with a specialized `PromptSpyLLMService` that records all prompts it receives instead of actually generating text.
**AND GIVEN** a set of `SemanticChunk` objects.
**WHEN** the `RaptorEngine` processes these chunks.
**THEN** the `PromptSpyLLMService` must record the prompts sent for summarization.
**AND** inspecting these recorded prompts must reveal specific keywords or instructions related to the Chain of Density methodology (e.g., the prompt must contain substrings like "summarize", "rewrite", "missing entities", or "density"). This proves the engine is not just asking for a simple summary, but specifically requesting the advanced CoD format required by the PRD.

### UAT-04-03: Tree Relational Integrity and Schema Enforcement
**GIVEN** a completely generated `EnrichedDocument` object (produced via the full pipeline in Mock Mode), containing both a list of `SemanticChunk` objects and a list of `RaptorNode` objects.
**WHEN** the test iterates through every `RaptorNode` in the document.
**THEN** for every ID found in a node's `children_ids` list, there must exist exactly one `SemanticChunk` in the document's `chunks` list with that identical UUID.
**AND WHEN** the test attempts to illegally assign a new, undeclared attribute directly to one of the `RaptorNode` objects (e.g., `node.invalid_field = "test"`).
**THEN** the Python runtime (via Pydantic) must immediately raise an error (or strictly ignore it depending on exact Pydantic `extra="forbid"` behavior during assignment, but typically it raises `ValueError` or `AttributeError` for forbidden extras on assignment in modern Pydantic), proving the domain objects remain immutable to structural changes even after creation.