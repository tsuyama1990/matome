# System Architecture: Matome 2.0 "Knowledge Installation"

## 1. Summary

The **Matome 2.0 "Knowledge Installation"** project represents a significant evolutionary leap from the existing static CLI-based summarization tool to a dynamic, interactive GUI-based knowledge acquisition system. The primary goal of this transformation is to shift the paradigm from "passive reading of summaries" to "active installation of knowledge." In the information age, users are bombarded with vast amounts of text. Traditional summarization tools merely compress this text, often losing the nuances or the structural logic that makes the information actionable or wise. Matome 2.0 addresses this by introducing the concept of **Semantic Zooming**, a user interface and underlying logic that allows users to traverse information at varying levels of abstraction—from high-level philosophical wisdom down to granular data evidence—much like zooming into a map.

At the heart of this system is the **DIKW (Data, Information, Knowledge, Wisdom) Reverse Logic**. Unlike standard summarization which simply shortens text, the Matome 2.0 engine will actively restructure content into a hierarchy:
-   **Wisdom (L1):** The root of the tree, capturing the core philosophy or "one-line takeaway" (e.g., "Invest in change, not just numbers").
-   **Knowledge (L2):** The frameworks and mental models that support the wisdom (e.g., "The mechanism of market anomalies").
-   **Information/Action (L3):** Actionable checklists and how-to guides derived from the knowledge (e.g., "Check PSR < 1.0").
-   **Data (L4):** The original source text chunks serving as evidence.

To achieve this, the system will undergo a major architectural refactoring. The monolithic `SummarizationAgent` will be decomposed using the **Strategy Pattern**, allowing for specialized prompting strategies for each level of the DIKW hierarchy. A new **Interactive Engine** layer will be introduced to handle real-time user requests, such as "rewrite this node to be simpler" or "expand on this concept," without requiring a full re-process of the document. This interactivity is powered by a **Panel-based GUI** designed with the **MVVM (Model-View-ViewModel)** pattern, ensuring a clean separation of concerns between the visual presentation and the underlying business logic.

The project is structured into **5 distinct development cycles**, ensuring a progressive and stable rollout of features. Starting with core logic refactoring, moving through the implementation of the DIKW engine and interactive capabilities, and culminating in a polished GUI with advanced semantic zooming features. This systematic approach ensures that each layer is robust and fully tested before the next is built upon it, minimizing technical debt and maximizing reliability.

Ultimately, Matome 2.0 aims to be more than just a tool; it is a "Thought Partner" that helps users construct a robust mental model of any complex text, enabling them to not just know *about* a topic, but to truly *understand* and *apply* it.

## 2. System Design Objectives

The design of Matome 2.0 is guided by several critical objectives that define its success and operational constraints. These objectives are prioritized to ensure the system is not only functional but also maintainable, scalable, and user-centric.

### 2.1. Semantic Zooming & DIKW Hierarchy
The primary functional objective is to realize **Semantic Zooming**. The system must capable of generating a strictly structured tree where each level corresponds to a specific cognitive depth (DIKW).
-   **Wisdom Generation:** The system must be able to synthesize extremely high-level, abstract insights that serve as the root of the knowledge tree. This requires advanced prompting strategies that encourage the LLM to think conceptually rather than just descriptively.
-   **Traceability:** A key constraint is that every piece of wisdom or knowledge must be traceable back to its source data. The user must be able to click on a high-level concept and "drill down" to see the specific paragraphs in the original text that support it. This builds trust and allows for verification.
-   **Distinctiveness:** Each level must feel distinct. Level 2 (Knowledge) must not just be a longer version of Level 1 (Wisdom); it must provide the *structural why*. Level 3 (Action) must provide the *practical how*.

### 2.2. Interactive Refinement (Human-in-the-Loop)
Unlike the previous batch-processing model, Matome 2.0 must support **Interactive Refinement**.
-   **Granular Updates:** The system must support updating a single node in the tree without triggering a cascade of re-summarization for the entire document. This requires a sophisticated "Interactive Engine" that can isolate a node's context, send a specific modification request to the LLM (e.g., "make this simpler"), and update the database in real-time.
-   **State Management:** The system must track which nodes have been manually edited by the user (`is_user_edited` flag) to prevent subsequent automated processes from overwriting human curation. This preserves the user's "mental model" construction efforts.

### 2.3. Architectural Decoupling & Maintainability
To support the complex requirements above, the system architecture must be significantly modularized.
-   **Prompt Strategy Pattern:** The logic for *how* to summarize must be decoupled from the *agent* that executes the summary. We will implement a `PromptStrategy` interface, allowing us to plug in different strategies (WisdomStrategy, ActionStrategy) without modifying the core agent code. This makes the system extensible for future "modes" (e.g., "Academic Mode", "Creative Mode").
-   **MVVM Pattern for GUI:** The Graphical User Interface (GUI) must be built using the Model-View-ViewModel (MVVM) pattern. This ensures that the UI code (Panel layout) is strictly separated from the business logic (Interactive Session). This decoupling facilitates testing the logic without needing to spawn a GUI instance and allows for easier UI iterations.

### 2.4. Robust Concurrency & Data Integrity
Moving from a single-user CLI to an interactive app introduces concurrency challenges.
-   **Database Safety:** The SQLite database (`chunks.db`) will be accessed by both the background generation processes and the foreground interactive GUI. The system must implement robust locking mechanisms and connection management (using Context Managers) to prevent database corruption or "database is locked" errors.
-   **Thread Safety:** The `InteractiveRaptorEngine` must be thread-safe, ensuring that user requests do not interfere with ongoing background tasks.

### 2.5. User Experience (UX) Quality
The final objective is to deliver a seamless "Aha! Moment" for the user.
-   **Latency:** Interactive operations (like refining a node) should be as fast as the LLM allows. The UI must provide immediate feedback (loading states, optimistic updates) to keep the user engaged.
-   **Visual Clarity:** The layout of the information must be intuitive. The "Pyramid Navigation" must naturally guide the user from the abstract to the concrete.

## 3. System Architecture

The system architecture of Matome 2.0 is designed as a layered application, separating the presentation layer (GUI), the application logic layer (Interactive Engine), and the data persistence layer (Store).

### 3.1. Components Overview
1.  **Presentation Layer (Panel GUI):**
    -   **App:** The entry point for the web application.
    -   **ViewModel (`InteractiveSession`):** Manages the state of the session (current view, selected node, user input). It binds to the View using reactive parameters (`param` library).
    -   **View Components:** Reusable UI components for the Tree Visualization, Chat Interface, and Detail View.

2.  **Application Layer (Interactive Engine):**
    -   **`InteractiveRaptorEngine`:** The central controller for the interactive session. It wraps the core RAPTOR logic but exposes methods for granular manipulation (`refine_node`, `get_children`, `get_parent`).
    -   **`SummarizationAgent`:** The worker that communicates with the LLM. It is now stateless regarding the *type* of summary, relying on the injected Strategy.
    -   **`PromptStrategy`:** A set of classes (`WisdomStrategy`, `KnowledgeStrategy`, `ActionStrategy`) that define the specific prompts and parsing logic for each DIKW level.

3.  **Data Layer:**
    -   **`DiskChunkStore`:** The abstraction over the SQLite database. It handles all read/write operations for Chunks and SummaryNodes. It ensures transactional integrity.
    -   **SQLite (`chunks.db`):** The persistent storage. It holds the document tree structure, embeddings, and text content.

### 3.2. Data Flow
1.  **Initialization:** The user loads a file. The `InteractiveRaptorEngine` checks if a tree exists. If not, it triggers the batch generation process using the `WisdomStrategy` for the root, then recursively down to `ActionStrategy`.
2.  **Navigation:** The user clicks a node (Wisdom). The GUI requests children from the `InteractiveRaptorEngine`. The Engine queries `DiskChunkStore` and returns the `Knowledge` nodes.
3.  **Refinement:** The user selects a `Knowledge` node and types "Simplify this".
    -   The GUI updates the ViewModel.
    -   The ViewModel calls `engine.refine_node(node_id, instruction="Simplify this")`.
    -   The Engine retrieves the node and its children (context) from the Store.
    -   The Engine selects the appropriate `PromptStrategy` (or uses a generic `RefinementStrategy`).
    -   The `SummarizationAgent` calls the LLM with the context and instruction.
    -   The LLM returns the new text.
    -   The Engine updates the node in `DiskChunkStore` with the new text and marks `is_user_edited=True`.
    -   The GUI observes the change and updates the text on screen.

### 3.3. Architecture Diagram

```mermaid
graph TD
    User((User)) -->|Interacts| GUI[Panel GUI (View)]
    GUI <-->|Binds| VM[InteractiveSession (ViewModel)]
    VM -->|Calls| Engine[InteractiveRaptorEngine]

    subgraph "Application Logic"
        Engine -->|Uses| Agent[SummarizationAgent]
        Engine -->|Reads/Writes| Store[DiskChunkStore]
        Agent -->|Uses| Strategy[PromptStrategy Interface]
        Strategy <|-- Wisdom[WisdomStrategy]
        Strategy <|-- Knowledge[KnowledgeStrategy]
        Strategy <|-- Action[ActionStrategy]
    end

    subgraph "Data Persistence"
        Store -->|SQL| DB[(SQLite: chunks.db)]
    end

    subgraph "External"
        Agent <-->|API| LLM[OpenAI / LLM Provider]
    end
```

## 4. Design Architecture

This section details the internal code structure and data models that underpin the system. The design adheres to strict typing (mypy), data validation (Pydantic), and clean architecture principles.

### 4.1. File Structure
The project structure is organized by domain and function. New directories and files are introduced to support the GUI and Strategy patterns.

```ascii
src/
├── domain_models/          # Pydantic Models (Shared Domain Kernel)
│   ├── types.py            # NodeID, Metadata
│   ├── manifest.py         # SummaryNode, DocumentTree (Updated for DIKW)
│   ├── dikw.py             # [NEW] DIKW specific enums and models
│   └── ...
├── matome/
│   ├── agents/
│   │   └── summarizer.py   # Refactored to use PromptStrategy
│   ├── engines/
│   │   ├── raptor.py       # Existing Batch Engine
│   │   └── interactive.py  # [NEW] InteractiveRaptorEngine
│   ├── strategies/         # [NEW] Prompt Strategy Implementations
│   │   ├── base.py         # Abstract Base Class / Protocol
│   │   ├── dikw.py         # Wisdom, Knowledge, Action Strategies
│   │   └── refinement.py   # Refinement Logic
│   ├── gui/                # [NEW] Panel GUI Application
│   │   ├── app.py          # Main Entry Point
│   │   ├── view_model.py   # InteractiveSession (MVVM)
│   │   └── components/     # Reusable UI Widgets
│   │       ├── zoom_view.py
│   │       └── chat_view.py
│   ├── utils/
│   │   └── store.py        # DiskChunkStore (Thread-safe enhancements)
│   └── ...
```

### 4.2. Key Data Models

**1. DIKW Level Enum (`src/domain_models/dikw.py`)**
```python
class DIKWLevel(str, Enum):
    WISDOM = "wisdom"       # L1
    KNOWLEDGE = "knowledge" # L2
    INFORMATION = "information" # L3 / Action
    DATA = "data"           # L4 / Raw Chunk
```

**2. Extended Node Metadata (`src/domain_models/types.py` / `manifest.py`)**
We extend the existing `metadata` dictionary in `SummaryNode` to strictly enforce DIKW attributes. While we may use a `TypedDict` or Pydantic model for validation within the code, the storage remains a JSON field.

```python
class NodeMetadata(BaseModel):
    dikw_level: DIKWLevel
    is_user_edited: bool = False
    refinement_history: List[str] = Field(default_factory=list)
    # ... existing metadata fields
```

**3. Interactive Session State (`src/matome/gui/view_model.py`)**
Using `param` library for reactive state management.

```python
class InteractiveSession(param.Parameterized):
    current_root_id = param.String()
    selected_node_id = param.String()
    chat_history = param.List()
    is_processing = param.Boolean(default=False)
    # ...
```

### 4.3. Class/Function Definitions Overview

**`PromptStrategy` Protocol:**
Defines the contract for all summarization strategies.
-   `get_system_prompt() -> str`: Returns the persona/instruction.
-   `get_user_prompt(context: str) -> str`: Formats the context into the prompt.
-   `parse_output(output: str) -> str`: Cleans/formats the LLM response.

**`InteractiveRaptorEngine` Class:**
-   `__init__(store: DiskChunkStore, agent: SummarizationAgent)`
-   `refine_node(node_id: NodeID, instruction: str) -> SummaryNode`: Main interactive method.
-   `get_tree_view(root_id: NodeID, depth: int) -> DocumentTree`: Returns a subtree for visualization.

## 5. Implementation Plan

The development is divided into 5 sequential cycles. Each cycle builds upon the previous one, ensuring a stable foundation.

### CYCLE 01: Core Logic Refactoring & DIKW Metadata
**Goal:** Prepare the codebase for DIKW and Strategies without breaking existing functionality.
-   **Refactoring:** Abstract the hardcoded prompts in `SummarizationAgent` into a `PromptStrategy` interface.
-   **Data Modeling:** Define `DIKWLevel` enum and update `SummaryNode` metadata expectations.
-   **Migration:** Ensure existing `RaptorEngine` can still function using a default `LegacyStrategy`.
-   **Verification:** Unit tests to ensure `SummarizationAgent` works with the new strategy interface.

### CYCLE 02: DIKW Generation Engine
**Goal:** Implement the specific logic to generate Wisdom, Knowledge, and Action nodes.
-   **Strategies:** Implement `WisdomStrategy` (High abstraction), `KnowledgeStrategy` (Structural), and `ActionStrategy` (Checklists) in `src/matome/strategies/dikw.py`.
-   **Engine Logic:** Update `RaptorEngine` (or create a subclass) to apply these strategies dynamically based on the tree depth or clustering results.
-   **Pipeline Integration:** Ensure that running the CLI with `--mode dikw` produces a tree with these specific characteristics.
-   **Verification:** Check output quality (manual inspection) and metadata correctness.

### CYCLE 03: Interactive Engine & DB Concurrency
**Goal:** Build the backend logic for interactivity and ensure it can handle concurrent access.
-   **Interactive Engine:** Create `InteractiveRaptorEngine`. Implement `refine_node` which isolates a node, applies a modification, and updates the DB.
-   **Concurrency:** Audit `DiskChunkStore`. Wrap all DB writes in strict context managers (`with transaction():`). Add retry logic for "database locked" errors using `tenacity`.
-   **State Management:** Implement logic to track `is_user_edited`.
-   **Verification:** Integration tests simulating concurrent reads/writes and verifying data consistency.

### CYCLE 04: GUI Foundation (MVVM & Basic View)
**Goal:** Create the basic Panel application skeleton and connect it to the engine.
-   **ViewModel:** Implement `InteractiveSession` using `param`. Handle loading the DB and tracking current selection.
-   **View:** Create the main `app.py`. Set up a basic layout (Sidebar, Main Area).
-   **Tree Visualization:** Implement a basic tree view (using `panel` or `networkx` integration) to display the node hierarchy.
-   **Verification:** Launch the app and verify that the tree loads and navigation (clicking a node updates the selection) works.

### CYCLE 05: Semantic Zooming & Interactive Refinement
**Goal:** Implement the "Wow" features—Semantic Zooming and Chat-based refinement.
-   **Semantic Zoom:** Polish the tree visualization to support "drilling down" (hiding/showing levels). Implement the "Pyramid" view logic.
-   **Chat Interface:** Create a chat component where users can type instructions. Connect this to `InteractiveRaptorEngine.refine_node`.
-   **Live Updates:** Ensure that when the engine updates the DB, the UI automatically refreshes the node text.
-   **Final Polish:** CSS styling, error handling, and user feedback (loading spinners).
-   **Verification:** Full User Acceptance Testing (UAT) scenarios.

## 6. Test Strategy

### General Approach
We will use `pytest` for all testing. The strategy involves a mix of unit tests for logic, integration tests for database/state, and functional tests for the engine.

### Cycle 01 Testing
-   **Unit Tests:** Create mocks for `SummarizationAgent` to verify it calls `PromptStrategy` methods correctly. Test `LegacyStrategy` to ensure it produces identical prompts to the old hardcoded version.
-   **Schema Tests:** Verify that `SummaryNode` validates the new metadata fields correctly (and allows them to be optional for backward compatibility).

### Cycle 02 Testing
-   **Strategy Unit Tests:** specific tests for `WisdomStrategy`, etc., feeding them sample inputs and asserting the prompt format is correct.
-   **Pipeline Integration Test:** Run a small dataset through the updated engine. Assert that the resulting nodes in `DiskChunkStore` have the correct `dikw_level` metadata set.

### Cycle 03 Testing
-   **Concurrency Tests:** Create a test using `ThreadPoolExecutor` where multiple threads try to read/write to `DiskChunkStore` simultaneously via `InteractiveRaptorEngine`. Verify no data corruption or unhandled exceptions.
-   **Refinement Logic Test:** Test `refine_node` in isolation. Mock the LLM to return a "fixed" string. Assert that the node in the DB is updated and `is_user_edited` is set to True.

### Cycle 04 Testing
-   **ViewModel Unit Tests:** Test `InteractiveSession` logic without the GUI. Assert that changing `selected_node_id` triggers the correct data fetching logic.
-   **Smoke Test:** A script that initializes the Panel app and checks if it renders without errors (headless mode if possible, or simple instantiation check).

### Cycle 05 Testing
-   **End-to-End (E2E) / UAT:** Since GUI testing is hard to automate without heavy tools like Playwright, we will rely heavily on the `UAT.md` scenarios.
-   **Scenario A (Zooming):** Manual verification that clicking root reveals children.
-   **Scenario B (Refinement):** Manual verification that typing in chat updates the node.
-   **Regression Test:** Ensure the CLI batch mode still works perfectly after all GUI additions.