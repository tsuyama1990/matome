# System Architecture: Matome 2.0 "Knowledge Installation"

## 1. Summary

The **Matome 2.0 "Knowledge Installation"** project represents a paradigm shift from traditional, static text summarization to a dynamic, interactive knowledge acquisition system. In an era of information overload, merely compressing text is insufficient; users require tools that enable them to reconstruct information into their own mental models. Matome 2.0 addresses this by transforming linear documents into a hierarchical **Data-Information-Knowledge-Wisdom (DIKW)** structure, allowing users to traverse from high-level philosophical insights ("Wisdom") down to actionable steps ("Information") and raw evidence ("Data").

At its core, the system utilizes the **RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)** algorithm, but with a significant twist: the "Semantic Zooming" engine. Unlike standard recursive summarization which simply condenses text at each level, Semantic Zooming applies distinct cognitive strategies at each hierarchy level. The root node acts as the "Wisdom" layer, distilling the document's essence into a profound, memorable aphorism. The intermediate branches form the "Knowledge" layer, explaining the *why* and *how*—the structural logic underpinning the wisdom. The lower branches serve as the "Information" layer, providing concrete, actionable checklists or procedures. Finally, the leaves are the original text chunks, serving as the "Data" or evidence layer.

Technically, Matome 2.0 evolves the existing Python-based CLI tool into a robust **Interactive GUI Application** built with the **Panel** framework. This transition necessitates a significant architectural overhaul to support stateful interactions, concurrent database access, and real-time content refinement. Users will no longer just run a script and read a Markdown file; they will interact with a "Matome Canvas." This interface starts by presenting only the core Wisdom. Users can then "zoom in" (drill down) to reveal supporting Knowledge and Information, effectively mimicking the way human experts explain complex topics—starting with the conclusion and elaborating on demand.

Furthermore, the system introduces **Interactive Refinement**. If a user finds a particular summary node unclear or misaligned with their needs (e.g., "too technical," "needs more examples"), they can instruct the system to regenerate just that specific node in real-time. This feedback loop allows the user to actively participate in the knowledge construction process, tailoring the final output to their specific cognitive style and context.

The architecture is designed for **modularity and extensibility**. Key components like the `SummarizationAgent` are refactored to use the **Strategy Pattern**, decoupling the core LLM interaction logic from the specific prompting strategies required for different DIKW levels. The data layer, powered by **SQLite** via `DiskChunkStore`, is enhanced to handle concurrent reads and writes, ensuring a smooth user experience even when the background engine is updating the graph. The GUI follows the **Model-View-ViewModel (MVVM)** pattern, ensuring a clean separation of concerns between the presentation logic and the underlying business rules. This comprehensive redesign ensures that Matome 2.0 is not just a feature update, but a robust platform for future "Knowledge Installation" innovations.

## 2. System Design Objectives

The design of Matome 2.0 is guided by several critical objectives, constraints, and success criteria that ensure the final product meets the high standards of a "Knowledge Installation" tool.

### 2.1. Goals

1.  **True Semantic Zooming (DIKW Hierarchy):**
    The primary goal is to move beyond generic summaries. The system must distinctly generate content that qualifies as Wisdom (L1), Knowledge (L2), and Information (L3). Wisdom must be abstract and philosophical; Knowledge must be structural and explanatory; Information must be actionable and concrete. The distinction must be qualitative, not just a difference in length.

2.  **Interactive Knowledge Construction:**
    The system must support an active user role. The "Matome Canvas" is not a static report but a workspace. Users must be able to explore the tree structure dynamically (drilling down) and modify it (refinement). The system response to these interactions must be near-real-time, fostering a sense of conversation with the document.

3.  **Seamless Integration of CLI and GUI:**
    While introducing a GUI, the system must retain its CLI capabilities for batch processing and automation. The architecture must share the core engine logic (`RaptorEngine`, `DiskChunkStore`) between both interfaces without code duplication. The GUI should be an extension, not a fork.

4.  **Robust Concurrency and State Management:**
    Transitioning to an interactive app introduces the challenge of state. The system must manage the state of the user's session (current view, selected node) and ensure that database operations (reading the tree, updating a node) do not conflict, especially given the potential for long-running background generation tasks.

### 2.2. Constraints

1.  **Dependency Management:**
    The project is constrained to use specific libraries: `langchain`, `openai`, `panel`, `watchfiles`, and standard scientific Python stacks (`numpy`, `scikit-learn`). Introducing heavyweight web frameworks like Django or FastAPI is outside the scope; the GUI must be self-contained within the Panel framework.

2.  **Performance and Latency:**
    LLM calls are inherently slow. The system design must mitigate the *perceived* latency. Operations like "drill down" should be instant (fetching from DB), while "refinement" (LLM generation) must provide immediate visual feedback (loading states) to keep the user engaged.

3.  **Data Integrity:**
    The system operates on a tree structure where parent nodes are derived from child nodes. The "Interactive Refinement" feature introduces a consistency challenge: if a child node is manually changed, does the parent need to update? For this phase, we accept loose consistency (parents don't auto-update immediately) to prioritize responsiveness, but the data model must track `is_user_edited` status to prevent overwrites.

### 2.3. Success Criteria

1.  **Distinct DIKW Quality:**
    A blind test of generated nodes should clearly categorize them into Wisdom, Knowledge, or Action based on their content style. "Wisdom" should sound like a proverb; "Action" should look like a checklist.

2.  **Stability under Concurrency:**
    The application must not crash or corrupt the SQLite database when the user navigates the tree while a background generation process is finalizing.

3.  **Refinement Responsiveness:**
    User requests to rewrite a node must complete successfully, and the updated text must persist in the `chunks.db` and be reflected in the UI immediately upon completion.

4.  **Clean Architecture:**
    The codebase must pass strict linting (`ruff`, `mypy` strict mode). The separation between the GUI layer (View/ViewModel) and the Engine layer (Model) must be strictly enforced, with no UI code leaking into the core logic.

## 3. System Architecture

The system follows a layered architecture, separating the User Interface (CLI & GUI) from the Core Application Logic (Engines) and the Data Layer (Store & Models). This separation ensures that the complex logic of RAPTOR and Semantic Zooming can be developed, tested, and maintained independently of the presentation layer.

### 3.1. High-Level Components

*   **Interfaces (CLI/GUI):** The entry points. The CLI (`matome.cli`) is used for batch ingestion and initial processing. The GUI (`matome.ui`) is the interactive Canvas for exploration and refinement.
*   **Controllers (Engines):**
    *   `InteractiveRaptorEngine`: The main orchestration controller for the GUI. It wraps the core logic and handles stateful operations like "update node X".
    *   `RaptorEngine`: The core batch processing engine responsible for the initial recursive summarization loop.
*   **Services (Agents & Utils):**
    *   `SummarizationAgent`: Encapsulates LLM interaction. Now enhanced with `PromptStrategy`.
    *   `Clusterer` / `Embedder` / `Chunker`: Specialized services for text processing.
*   **Data Layer:**
    *   `DiskChunkStore`: A Thread-safe SQLite wrapper for persisting the Document Tree.
    *   `Domain Models`: Pydantic models defining the schema for `SummaryNode`, `Chunk`, etc.

### 3.2. Data Flow

1.  **Ingestion (CLI):** User inputs a text file -> `Chunker` splits it -> `Embedder` vectorizes it -> `RaptorEngine` builds the DIKW Tree -> `DiskChunkStore` saves it.
2.  **Exploration (GUI):** User opens GUI -> `InteractiveSession` loads Root Node (Wisdom) from `DiskChunkStore` -> Displays in `MatomeCanvas`.
3.  **Drill-Down (GUI):** User clicks Root -> `InteractiveSession` queries Children IDs -> Fetches Nodes (Knowledge) from `DiskChunkStore` -> Updates View.
4.  **Refinement (GUI):** User sends "Rewrite" prompt -> `InteractiveRaptorEngine` calls `SummarizationAgent` with specific `PromptStrategy` -> LLM generates new text -> `DiskChunkStore` updates Node -> View reflects change.

### 3.3. Diagram

```mermaid
graph TD
    subgraph "Presentation Layer"
        CLI[CLI (Typer)]
        GUI[GUI (Panel App)]
        ViewModel[InteractiveSession (ViewModel)]
    end

    subgraph "Application Layer"
        IRE[InteractiveRaptorEngine]
        RE[RaptorEngine]
        SA[SummarizationAgent]
        PS[PromptStrategy (Interface)]
        PS_W[WisdomStrategy]
        PS_K[KnowledgeStrategy]
        PS_A[ActionStrategy]
    end

    subgraph "Domain Services"
        Chunker
        Embedder
        Clusterer
    end

    subgraph "Data Layer"
        Store[DiskChunkStore (SQLite)]
        Models[Domain Models (Pydantic)]
    end

    %% Connections
    CLI --> RE
    GUI --> ViewModel
    ViewModel --> IRE
    IRE --> Store
    IRE --> SA
    RE --> Store
    RE --> SA
    RE --> Chunker
    RE --> Embedder
    RE --> Clusterer

    SA --> PS
    PS <|.. PS_W
    PS <|.. PS_K
    PS <|.. PS_A

    Store --> Models
```

## 4. Design Architecture

The codebase is structured to enforce separation of concerns and maintainability. We utilize **Pydantic V2** for robust data validation and **Protocol-based interfaces** for dependency injection.

### 4.1. File Structure

```ascii
src/matome/
├── agents/
│   ├── __init__.py
│   ├── summarizer.py       # Core Agent
│   ├── strategies.py       # NEW: Prompt Strategies (Wisdom, Knowledge, Action)
│   └── verifier.py
├── engines/
│   ├── __init__.py
│   ├── interactive.py      # NEW: Interactive Engine Wrapper
│   ├── raptor.py           # Core Batch Engine
│   ├── chunker.py
│   ├── cluster.py
│   └── embedder.py
├── ui/                     # NEW: GUI Package
│   ├── __init__.py
│   ├── app.py              # Panel Entry Point
│   ├── view_model.py       # MVVM ViewModel
│   └── components.py       # UI Components
├── utils/
│   ├── store.py            # SQLite Store
│   └── prompts.py
├── interfaces.py
├── config.py
└── main.py
src/domain_models/
├── manifest.py             # SummaryNode, Chunk, DocumentTree
├── metadata.py             # NEW: Metadata Schemas
└── types.py
```

### 4.2. Key Data Models

1.  **SummaryNode (Modified):**
    The central entity. We add a robust `metadata` schema to handle the DIKW logic.
    *   `id`: UUID
    *   `text`: The content.
    *   `children_indices`: Links to lower levels.
    *   `metadata`: `NodeMetadata` object.

2.  **NodeMetadata (New):**
    *   `dikw_level`: Enum (`wisdom`, `knowledge`, `information`, `data`).
    *   `is_user_edited`: boolean. Locks the node from auto-updates.
    *   `prompt_history`: List of prompts used to generate/refine this node.

3.  **PromptStrategy (Protocol):**
    A new interface to define how a summary is generated.
    *   `generate_prompt(context: str, existing_summary: str | None) -> str`
    *   `parse_response(response: str) -> str`

### 4.3. Class/Function Definitions Overview

*   **`InteractiveRaptorEngine`**:
    *   `__init__(store, agent)`: Injects dependencies.
    *   `refine_node(node_id, instruction)`: The core method for user interaction. It retrieves the node, selects the appropriate strategy based on the instruction (or defaults), calls the agent, and updates the store.
    *   `get_tree_view(root_id, depth)`: Helper to fetch a subtree for visualization.

*   **`InteractiveSession` (ViewModel)**:
    *   `current_root`: The currently focused top-level node.
    *   `expanded_nodes`: Set of node IDs that are "open".
    *   `selected_node`: The node currently being edited.
    *   `drill_down(node_id)`: Updates `expanded_nodes`.
    *   `submit_refinement(instruction)`: Calls `InteractiveRaptorEngine.refine_node`.

*   **`PromptStrategy` implementations**:
    *   `WisdomStrategy`: Uses a prompt optimized for aphorisms and philosophical abstraction.
    *   `ActionStrategy`: Uses a prompt forcing checkbox/bullet-point output.

## 5. Implementation Plan

The project is divided into 5 distinct cycles, each building upon the last to transform the system from a CLI tool to a full Interactive Knowledge Suite.

### Cycle 01: Core Refactoring - Metadata & Strategy Pattern
**Focus:** Foundation. Preparing the data structures and agent logic.
**Features:**
*   **Refactor `SummarizationAgent`:** Introduce the `PromptStrategy` Protocol.
*   **Implement Strategies:** Create `BaseSummaryStrategy` (legacy) and placeholder DIKW strategies.
*   **Update `SummaryNode`:** Modify `domain_models/manifest.py` to enforce the new metadata schema (`dikw_level`, `is_user_edited`).
*   **Update `DiskChunkStore`:** Ensure it can handle the new metadata fields correctly (JSON serialization updates if needed).
**Goal:** The system runs exactly as before (CLI works), but the internal code is ready for DIKW logic.

### Cycle 02: DIKW Generation Engine
**Focus:** The "Brain". Implementing the Semantic Zooming logic.
**Features:**
*   **Implement DIKW Strategies:** Develop specific `WisdomStrategy`, `KnowledgeStrategy`, and `ActionStrategy` classes with optimized prompts.
*   **Tree Construction Logic:** Modify `RaptorEngine` (or create a configuration mode) to apply these strategies based on tree depth.
    *   Leaves -> L1 (Action Strategy)
    *   L1 -> L2 (Knowledge Strategy)
    *   L2 -> Root (Wisdom Strategy)
*   **Tree Validation:** Ensure the generated tree respects the DIKW hierarchy.
**Goal:** The CLI `run` command now produces a tree where the root is Wisdom and leaves are Data.

### Cycle 03: Interactive Engine & Concurrency
**Focus:** The "Backend". Enabling safe interactive operations.
**Features:**
*   **`InteractiveRaptorEngine`:** Create the wrapper class in `src/matome/engines/interactive.py`.
*   **Single Node Refinement:** Implement `refine_node(node_id, user_instruction)` logic.
*   **Thread-Safe Store:** enhance `DiskChunkStore` usage patterns (verify WAL mode, add explicit context managers for transaction isolation) to support concurrent reads (GUI) and writes (Refinement).
**Goal:** We can programmatically (via Python script) load an existing DB and update a specific node safely.

### Cycle 04: GUI Foundation (MVVM)
**Focus:** The "Frontend" Skeleton.
**Features:**
*   **Panel Setup:** Initialize the `src/matome/ui` package.
*   **ViewModel (`InteractiveSession`):** Create the class using `param` to manage application state (loaded tree, selection).
*   **Basic View:** Create a simple Panel layout that displays the Root Node (Wisdom) text.
*   **Connect:** Wire the `InteractiveSession` to the `InteractiveRaptorEngine`.
**Goal:** We can launch the app (`panel serve`), load a DB, and see the Wisdom node.

### Cycle 05: Semantic Zooming & Refinement
**Focus:** The "Experience". Completing the user journey.
**Features:**
*   **Drill-Down UI:** Implement the visual logic to show children nodes when a parent is clicked.
*   **Refinement UI:** Add the Chat interface / Text Input for the "Refine" action.
*   **Live Updates:** Use `param.watch` or Panel's reactive binding to update the text on screen immediately after the backend updates the DB.
*   **Final Polish:** Styling, error handling, and usability improvements.
**Goal:** The complete "Matome 2.0" experience as defined in the UAT.

## 6. Test Strategy

We employ a rigorous testing strategy combining Unit Tests, Integration Tests, and User Acceptance Tests (UAT) to ensure reliability and quality.

### Cycle 01 Testing
*   **Unit Tests:**
    *   Test `SummarizationAgent` with a mock `PromptStrategy` to ensure the strategy is correctly invoked.
    *   Test `SummaryNode` Pydantic validation to ensure `dikw_level` is required and validated.
    *   Test `DiskChunkStore` serialization/deserialization with the new metadata fields.
*   **Integration Tests:**
    *   Run the existing `test_raptor_pipeline.py` to ensure no regressions in the core flow.
    *   Verify that generated summaries in the DB now have the default `dikw_level` metadata.

### Cycle 02 Testing
*   **Unit Tests:**
    *   Test each Strategy (`WisdomStrategy`, etc.) in isolation: Input a text -> Mock LLM -> Verify prompt format.
*   **Integration Tests:**
    *   Run the full pipeline (`RaptorEngine.run`) with the new DIKW configuration.
    *   **Manual Inspection:** Check the generated `summary_dikw.md` (or DB content). Does the root node sound like Wisdom? Do the leaf-summaries look like Actions?
    *   **Automated DIKW Verification:** A test script that traverses the generated tree and asserts that Level 0 summaries have `dikw_level='information'` (or as configured) and the Root has `dikw_level='wisdom'`.

### Cycle 03 Testing
*   **Unit Tests:**
    *   Test `InteractiveRaptorEngine.refine_node`: Mock the LLM and Store. Verify that the correct node is fetched, updated, and saved.
*   **Concurrency Tests:**
    *   Create a test that spawns a thread reading from `DiskChunkStore` while another thread uses `InteractiveRaptorEngine` to update nodes. Verify no `sqlite3.OperationalError: database is locked` occurs.
    *   Verify data consistency: The read thread should eventually see the update.

### Cycle 04 Testing
*   **Unit Tests:**
    *   Test `InteractiveSession` (ViewModel): Call `drill_down`, assert `expanded_nodes` state changes. Call `select_node`, assert `selected_node` updates.
*   **UI Launch Test:**
    *   A script that initializes the App and checks if the server starts without errors.
    *   (Optional) Use Playwright to screenshot the initial load state (Wisdom Card visible).

### Cycle 05 Testing
*   **End-to-End (E2E) UAT:**
    *   **Scenario:** "The Aha! Moment".
    *   1. Launch App.
    *   2. Verify Wisdom is displayed.
    *   3. Click Wisdom -> Verify Knowledge nodes appear.
    *   4. Click a Knowledge node -> Verify Action nodes appear.
    *   5. Select an Action node -> Type "Make it shorter" -> Verify text updates on screen and in DB.
    *   This will be performed manually or via a recorded Playwright script if feasible.
