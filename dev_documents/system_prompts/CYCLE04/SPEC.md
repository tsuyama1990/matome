# CYCLE 04: RAPTOR Tree Generation & Summarization

## Summary
Building directly upon the semantic chunking accomplished in Cycle 03, Cycle 04 tackles the core architectural innovation of the `matome` system: the RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) hierarchical tree generation. This cycle transforms the flat list of `SemanticChunk` objects into a multi-level `RaptorNode` hierarchy, enabling the "Semantic Zooming" UI and overcoming the cognitive overload associated with flat documents. We will implement the complex pipeline that clusters chunks based on their semantic embeddings (using UMAP for dimensionality reduction and Gaussian Mixture Models (GMM) for soft clustering), and then orchestrates the LLM to generate highly dense, "Chain of Density" (CoD) summaries for each resulting cluster.

This cycle represents the most computationally intensive and AI-heavy portion of the backend. We will introduce `scikit-learn` and `umap-learn` to handle the mathematical clustering, taking care to wrap these heavy dependencies defensively to prevent module loading failures if they are missing in certain environments. The output of this cycle is the fully populated `EnrichedDocument` domain model, which encapsulates both the raw chunks and the navigable summary tree, ready to be served to the frontend for interactive learning.

## System Architecture

The architecture for Cycle 04 extends the Application Layer (`src/application/`) by introducing the `RaptorEngine` service. This engine takes the output of the `IngestionPipeline` (a list of `SemanticChunk`s) and processes it to create `RaptorNode` objects. It relies heavily on the `LLMProtocol` (for generating summaries via the Chain of Density prompt) and mathematical libraries (`umap`, `sklearn`) for clustering. The final output is the `EnrichedDocument` model, containing the full state required by the UI. We will ensure the mathematical operations are abstracted behind a clean interface or functional boundary to maintain testability and adherence to DDD principles.

```text
matome/
├── src/
│   ├── domain_models/
│   │   ├── document.py        (Existing: RaptorNode, EnrichedDocument)
│   ├── interfaces/
│   │   ├── llm_protocol.py    (Existing)
│   ├── **application/**
│   │   ├── ingestion.py       (Existing)
│   │   ├── **raptor_engine.py**   (NEW: Clustering and Summarization logic)
│   ├── **infrastructure/**
│   │   ├── **clustering.py**      (NEW: Wrapper for UMAP/GMM)
```

## Design Architecture

This cycle focuses on complex data transformations and orchestrating multiple LLM calls to build the hierarchical structure.

### 1. `src/infrastructure/clustering.py`
*   **`SemanticClusterer`**: A class responsible for the heavy mathematical lifting.
    *   **Defensive Imports**: It MUST wrap `import umap` and `sklearn.mixture` in `try/except ImportError` blocks. If these libraries are unavailable, it should set a flag (e.g., `_ML_AVAILABLE = False`) and raise a clear `ImportError` or custom domain exception only when its methods are actually called, preventing the entire application from crashing on startup if these heavy dependencies are missing.
    *   **`cluster_embeddings(embeddings: np.ndarray) -> dict[int, list[int]]`**: This method takes a 2D NumPy array of embeddings. It must first assert the shape is 2D. It uses UMAP to reduce dimensionality (e.g., to 2D or 3D for clustering stability) and then GMM to form clusters. It returns a mapping of cluster IDs to the indices of the chunks belonging to that cluster.
    *   **Edge Case Handling**: As specified in the memory constraints, if the number of samples (`n_samples`) is less than or equal to the desired number of clusters (or `< 3`), it must bypass GMM entirely to prevent `ValueError: ill-conditioned covariance` exceptions, returning a trivial clustering (e.g., `{0: [0]}` for 1 chunk).

### 2. `src/application/raptor_engine.py`
*   **`RaptorEngine`**: The core application service for building the tree.
    *   **Dependencies**: Requires `LLMProtocol` injected via `__init__`.
    *   **`build_tree(chunks: list[SemanticChunk]) -> list[RaptorNode]`**: The main orchestration method.
        1.  **Extract Embeddings**: Convert the embeddings from the `SemanticChunk` list into a NumPy array.
        2.  **Cluster**: Call `SemanticClusterer.cluster_embeddings`.
        3.  **Summarize (Chain of Density)**: For each cluster, concatenate the text of its constituent chunks. Concurrently (using `asyncio.gather`), call the `LLMProtocol` with a specific CoD prompt (e.g., "Summarize this text. Then, iteratively rewrite the summary 3 times, each time adding 2 missing entities while keeping the length identical").
        4.  **Create Nodes**: Instantiate `RaptorNode` objects for each summarized cluster. The `children_ids` will map to the original chunk IDs.
        5.  **Recursion (Optional for Cycle 04, but planned)**: If the number of resulting nodes is still too large, repeat the process on the newly generated `RaptorNode` summaries to build higher levels of the tree until a single root node (or a small handful) remains.

## Implementation Approach

1.  **Implement `SemanticClusterer`**: Create `src/infrastructure/clustering.py`. Implement the defensive imports for `umap` and `sklearn`. Write the `cluster_embeddings` method, ensuring it handles the `n_samples < 3` edge case gracefully by returning a dictionary mapping a cluster ID to the list of chunk indices.
2.  **Develop `RaptorEngine`**: Create `src/application/raptor_engine.py`. Define the class and inject `LLMProtocol`.
3.  **Implement `build_tree` Orchestration**:
    *   Extract the `embedding` attribute from each `SemanticChunk` into a `numpy.ndarray`. Validate its shape.
    *   Pass the array to the `SemanticClusterer`.
    *   Iterate over the returned cluster dictionary. For each cluster (list of indices), retrieve the corresponding `SemanticChunk.content`.
    *   Implement an asynchronous helper method `_generate_cod_summary(text: str)` that calls `self.llm.generate_text` with the Chain of Density prompt.
    *   Use `asyncio.gather` to execute these summarizations in parallel for all clusters.
    *   Construct a `RaptorNode` for each result, ensuring the Pydantic validation passes.
4.  **Integration with Ingestion**: Update the `IngestionPipeline` (or a higher-level orchestrator) to call `RaptorEngine.build_tree` after chunking, and finally instantiate the `EnrichedDocument` with both the chunks and the nodes.

## Test Strategy

The testing strategy for Cycle 04 is challenging due to the heavy machine learning dependencies and complex LLM prompts. We must rely heavily on mock modes and deterministic test doubles to ensure the core orchestration logic is sound without requiring GPUs or expensive API calls during CI.

**Unit Testing Approach (Minimum 300 words):**
We will start by thoroughly testing the `SemanticClusterer` in isolation. To test the mathematical logic without massive datasets, we will use small, artificial, mathematically distinct sets of 2D coordinates (e.g., three points tightly clustered around (0,0) and three points around (10,10)). We will assert that `cluster_embeddings` correctly identifies these two distinct clusters and returns the expected dictionary structure. Crucially, we will explicitly test the edge case defined in the memory constraints: we will pass only one or two dummy embeddings and assert that the method bypasses GMM, avoids crashing, and returns a fallback hierarchical mapping (e.g., `{0: [0]}` or `{0: [0, 1]}`). We will also test the defensive import logic by temporarily monkeypatching `sys.modules` to simulate a missing `umap` library and verifying that the `SemanticClusterer` initialization handles it gracefully according to the specification.

Next, we will unit test the `RaptorEngine` orchestration logic. We will mock the `SemanticClusterer` (since we just tested it) to return a predictable, hardcoded clustering dictionary (e.g., `{0: [0, 1], 1: [2]}`). We will inject the `DummyLLMService` from previous cycles into the `RaptorEngine`. We will provide a list of three dummy `SemanticChunk` objects.

When we call `build_tree`, we will assert that the `RaptorEngine` correctly groups the chunks according to the mocked cluster dictionary. We will assert that it makes exactly two asynchronous calls to the `DummyLLMService` (one for cluster 0 containing chunks 0 and 1, and one for cluster 1 containing chunk 2). We will intercept the prompts sent to the dummy LLM and assert that they contain the string "summarize" or "density" (validating the CoD prompt construction). Finally, we will assert that the method returns a list of exactly two `RaptorNode` objects, and that their `children_ids` correctly map to the original chunk IDs. This proves the complex grouping and parallel LLM orchestration logic is correct.

**Integration Testing Approach (Minimum 300 words):**
The integration tests for Cycle 04 will focus on the complete pipeline from raw text to the final `EnrichedDocument` Pydantic model, operating entirely in "Mock Mode".

We will configure the `DIContainer` with the `DummyLLMService`, `DummyEmbeddingService`, and the `PlainTextParser`. We will also configure it to use a "MockClusterer" (or the real `SemanticClusterer` if dependencies are guaranteed, but a mock is safer for CI stability) that simply groups adjacent chunks into pairs.

We will run the full ingestion process on a substantial test document (e.g., `tests/fixtures/sample_article.txt`). We will retrieve the resulting `EnrichedDocument` object. The test will perform extensive validation on this final object:
1.  **Chunk Integrity**: Assert that `EnrichedDocument.chunks` is a populated list of valid `SemanticChunk` objects.
2.  **Tree Structure**: Assert that `EnrichedDocument.raptor_nodes` is a populated list of valid `RaptorNode` objects.
3.  **Relational Consistency**: We will iterate through every `RaptorNode` and assert that every ID listed in its `children_ids` list actually exists within the `EnrichedDocument.chunks` list. This is a critical validation step ensuring no "dangling pointers" exist in the generated graph structure.
4.  **Schema Enforcement**: Finally, we will attempt to illegally modify the `EnrichedDocument` (e.g., by adding a non-existent field to a `RaptorNode` directly in memory) and assert that Pydantic prevents it, proving the `extra="forbid"` configuration remains active on the final output. This comprehensive test proves the entire architectural pipeline successfully transforms raw data into a strictly validated, highly structured knowledge graph ready for user interaction.