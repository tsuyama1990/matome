# User Test Scenario & Tutorial Strategy

## Tutorial Strategy

The primary goal of the User Acceptance Testing (UAT) and tutorial strategy for the `matome` platform is to provide a seamless, executable, and reproducible way to verify the entire system architecture. Because `matome` is a complex AI orchestration platform, traditional unit tests are insufficient to demonstrate the value proposition to a user or auditor.

We will adopt a strategy based on **Executable Notebooks**. Specifically, we will use **Marimo** (`marimo`), a reactive Python notebook environment. This approach allows us to blend explanatory Markdown text with executable Python code that interacts directly with the system's core APIs and domain models.

### "Mock Mode" vs. "Real Mode"

A critical requirement for this strategy is the ability to execute the entire tutorial without requiring paid external API keys (like OpenRouter) or complex infrastructure setups (like a running Pinecone instance).

*   **Mock Mode (Default):** The tutorial will be designed to run entirely in "Mock Mode" by default. This is achieved through the system's Dependency Injection (`DIContainer`) architecture. When initialized in Mock Mode, the application injects deterministic test doubles (e.g., `DummyLLMService`, `DummyEmbeddingService`, `DummyVectorDB`) instead of real clients. This ensures the notebook executes instantaneously, predictably, and without cost, making it ideal for CI/CD pipelines and initial user familiarization.
*   **Real Mode:** The notebook will include clear instructions and a configuration toggle (e.g., setting `MATOME_MOCK_MODE=False` and providing an `.env` file with an `OPENROUTER_API_KEY`). When switched to Real Mode, the DI container will automatically wire up the real infrastructure clients, allowing the user to experience the actual AI-powered insights using real documents. The code itself will not change; only the underlying injected dependencies will change.

## Tutorial Plan

We will create a **SINGLE** executable Marimo file to serve as both the comprehensive UAT suite and the user tutorial. Consolidating into one file reduces cognitive load and provides a single narrative flow from basic ingestion to advanced insights.

**Target File:** `tutorials/UAT_AND_TUTORIAL.py`

This file will be structured logically, mirroring the development cycles, to guide the user through the system's capabilities:

### Section 1: Introduction and Configuration (Cycle 01 & 02)
*   **Narrative:** Introduction to `matome` and the importance of secure configuration and Dependency Injection.
*   **Action:** The notebook will initialize the `AppConfig` and the `DIContainer`. It will demonstrate how the system handles missing API keys and how "Mock Mode" is activated.
*   **Verification:** Asserting that the container successfully resolves abstract protocols (like `LLMProtocol`) to the appropriate implementations (mock or real) based on the environment.

### Section 2: Document Ingestion and Chunking (Cycle 03)
*   **Narrative:** Explaining the "Lost-in-the-Middle" problem and how semantic chunking solves it.
*   **Action:** The user will provide a sample text string (or load a small local file). The notebook will invoke the `IngestionPipeline` to process the text.
*   **Verification:** Inspecting the resulting `SemanticChunk` objects, specifically checking that the text was logically divided, entities were extracted (or mocked), and the embeddings meet the strict dimensionality requirements of the Pydantic schema.

### Section 3: RAPTOR Tree Generation (Cycle 04)
*   **Narrative:** Demonstrating how to combat cognitive overload by building a hierarchical summary tree.
*   **Action:** The notebook will take the chunks from Section 2 and pass them through the `RaptorEngine` to build the tree structure.
*   **Verification:** Examining the resulting `EnrichedDocument`. The notebook will visualize (or print out) the `RaptorNode` hierarchy, verifying that nodes correctly point to their child chunks and contain the highly dense "Chain of Density" summaries.

### Section 4: Interactive Learning (SQ3R) (Cycle 05)
*   **Narrative:** Showcasing the gamified learning loop (Survey, Question, Read, Recite, Review).
*   **Action:** The notebook will simulate a user session using the `SQ3REngine` and `LearningProgress` models. It will pick a locked node, ask the engine to generate a question, simulate the user answering, and evaluate the answer.
*   **Verification:** Asserting that the user's progress state correctly updates (the node unlocks) only when a correct answer is provided, demonstrating the state machine logic.

### Section 5: Advanced Insights (Pivot KJ) (Cycle 06)
*   **Narrative:** The grand finale: demonstrating the transition from reading to creating by reconstructing the knowledge graph along new axes.
*   **Action:** The notebook will use the `PivotEngine` to reorganize the `EnrichedDocument` based on a requested axis (e.g., "SWOT Analysis"). Finally, it will use the `ExportService` to generate a Markdown report.
*   **Verification:** Inspecting the final `PivotState` and the generated Markdown string to ensure the information was correctly restructured and formatted according to the requested axis.

## Tutorial Validation

To ensure the tutorial is always functional and serves as a valid UAT artifact, it must be validated programmatically.

1.  **Headless Execution:** In CI environments, the tutorial must be executed using the command: `uv run marimo run tutorials/UAT_AND_TUTORIAL.py --headless`.
2.  **No Hanging:** The `--headless` flag is critical to prevent the process from hanging indefinitely while waiting for a browser connection.
3.  **Exit Status:** The execution must exit with code `0`. Any assertion failures or unhandled exceptions within the notebook cells will cause a non-zero exit code, immediately flagging a regression in the system architecture or domain models.
4.  **Mock Mode Guarantee:** This headless execution will *always* run in "Mock Mode" to ensure deterministic, cost-free validation of the logical flow.