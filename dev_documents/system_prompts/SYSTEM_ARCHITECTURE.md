# System Architecture

## 1. Summary

Matome 2.0 represents a paradigm shift in how we process and interact with large textual information. In an era of information overload, traditional summarization tools often fail because they produce a single, static block of text that is either too detailed or too abstract. Matome 2.0 addresses this by introducing the concept of **"Semantic Zooming"**—a dynamic, hierarchical approach to knowledge management based on the DIKW (Data, Information, Knowledge, Wisdom) model.

At its core, Matome 2.0 transforms linear documents—such as books, technical reports, and long-form articles—into an interactive knowledge graph. Instead of passively reading a summary, users can actively explore the content at different levels of abstraction. They can start at the **Wisdom** level, absorbing profound, context-free insights in seconds. If a particular insight resonates or requires clarification, they can "zoom in" to the **Knowledge** level to understand the underlying mental models and structural logic. Further zooming reveals actionable **Information** (checklists, procedures) and finally the raw **Data** (original text chunks) for verification.

This system is built upon a robust, modular architecture designed for extensibility and interactivity. The backend leverages the RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) methodology, enhanced with a custom **InteractiveRaptorEngine** that supports granular, random-access updates. This allows users to not only view the summary but also refine it. If a specific node in the knowledge graph is unclear or misaligned with the user's mental model, they can instruct the AI to rewrite it (e.g., "Explain this using a cooking analogy"). The system updates only the affected node and its metadata without the computational cost of regenerating the entire tree.

The frontend is architected using the **Model-View-ViewModel (MVVM)** pattern with the Panel library, ensuring a clean separation between the reactive user interface and the complex backend logic. This design supports a responsive, modern web application experience where users can navigate through breadcrumbs, visualize the hierarchy, and trace every insight back to its source evidence. By combining advanced NLP techniques with a user-centric design, Matome 2.0 empowers users to "install" knowledge directly into their minds, bridging the gap between raw data and true understanding.

## 2. System Design Objectives

The development of Matome 2.0 is guided by five critical design objectives, each ensuring the system is robust, scalable, and user-friendly.

### 2.1. Semantic Zooming (DIKW Hierarchy)
The primary objective is to faithfully implement the DIKW hierarchy as a navigational structure.
- **Wisdom (L1):** The system must be capable of synthesizing thousands of words into 20-40 character aphorisms that capture the "soul" of the text. This requires a specialized prompting strategy that prioritizes abstraction over detail.
- **Knowledge (L2):** The system must extract structural understanding—mental models, frameworks, and causal relationships ("Why" and "How")—rather than just facts.
- **Information (L3):** The output must be actionable. The system should identify procedures and convert them into checklists or step-by-step guides ("What to do").
- **Data (L4):** The system must maintain strict traceability. Every node in the hierarchy must preserve a link to its child nodes and, ultimately, the original text chunks (Data).

### 2.2. Granular Interactivity & Refinement
Unlike batch-oriented summarizers, Matome 2.0 must support real-time user interaction.
- **Single-Node Update:** The backend must support the invalidation and regeneration of individual nodes. This "Refinement" feature allows users to customize the summary.
- **State Management:** The system must track the history of refinements (`refinement_history`) to provide an audit trail and allow for undo/redo functionality in future versions.
- **Latency:** Interactive operations must be responsive. The architecture should avoid blocking the main UI thread during LLM generation.

### 2.3. Separation of Concerns (MVVM Architecture)
To ensure long-term maintainability and testability, the system must enforce a strict separation between the UI and the business logic.
- **ViewModel:** We will use the `InteractiveSession` class as a ViewModel. It will hold the application state (current selection, view mode, refinement text) and expose reactive parameters using the `param` library.
- **View:** The `MatomeCanvas` will be a pure projection of the ViewModel state, implemented with Panel. It will contain no business logic.
- **Model:** The `InteractiveRaptorEngine` and `DiskChunkStore` will encapsulate the data persistence and LLM orchestration logic.

### 2.4. Extensible Prompt Strategy Pattern
The summarization logic must be decoupled from the execution agent.
- **Strategy Injection:** The `SummarizationAgent` should accept a `PromptStrategy` implementation at runtime. This allows us to easily add new modes (e.g., "Socratic Mode", "ELI5 Mode") without modifying the core agent code.
- **Protocol Definition:** A strictly typed `Protocol` will define the contract for `format_prompt` and `parse_output`, ensuring all strategies are interchangeable and type-safe.

### 2.5. Data Consistency & Concurrency
Since the system involves both background generation tasks and interactive frontend requests, data integrity is paramount.
- **Thread Safety:** Access to the `chunks.db` SQLite database must be thread-safe. We will implement robust context managers to handle connections and locking, ensuring that a user's refinement action doesn't corrupt a concurrent read operation.
- **Validation:** All data entering the system must be validated against Pydantic schemas (`NodeMetadata`) to prevent malformed data from propagating through the hierarchy.

## 3. System Architecture

The high-level architecture is designed as a layered system, ensuring that data flows logically from raw text to the interactive user interface.

```mermaid
graph TD
    subgraph "Data Layer"
        RawText[Raw Text File]
        DB[(chunks.db)]
        ChunkStore[DiskChunkStore]
    end

    subgraph "Core Engines"
        Chunker[JapaneseSemanticChunker]
        Embedder[EmbeddingService]
        Clusterer[GMMClusterer]
        Agent[SummarizationAgent]
    end

    subgraph "Strategy Layer"
        Strategy[PromptStrategy Protocol]
        WisdomStrat[WisdomStrategy]
        KnowledgeStrat[KnowledgeStrategy]
        InfoStrat[InformationStrategy]
        RefineStrat[RefinementStrategy]
    end

    subgraph "Interactive Backend"
        IRE[InteractiveRaptorEngine]
    end

    subgraph "Presentation Layer (MVVM)"
        Session[InteractiveSession (ViewModel)]
        Canvas[MatomeCanvas (View)]
    end

    RawText --> Chunker
    Chunker --> Embedder
    Embedder --> Clusterer
    Clusterer --> IRE

    IRE --> ChunkStore
    ChunkStore <--> DB

    IRE --> Agent
    Agent --> Strategy
    WisdomStrat -.-> Strategy
    KnowledgeStrat -.-> Strategy
    InfoStrat -.-> Strategy
    RefineStrat -.-> Strategy

    Session --> IRE
    Session --> ChunkStore
    Canvas --> Session
```

### Component Interaction Flow
1.  **Data Ingestion:** The `JapaneseSemanticChunker` splits the raw text into semantically meaningful chunks. `EmbeddingService` converts these into vectors.
2.  **Clustering (RAPTOR):** `GMMClusterer` groups similar chunks. This happens recursively to build the tree structure.
3.  **Summarization:** The `SummarizationAgent` generates summaries for each cluster. Crucially, it uses the injected `PromptStrategy` (Wisdom/Knowledge/Information) to determine the content and style of the summary.
4.  **Storage:** The `InteractiveRaptorEngine` coordinates these processes and stores the resulting `SummaryNode` objects in `chunks.db` via the `DiskChunkStore`.
5.  **Interactive Session:** The user launches `MatomeCanvas`. The `InteractiveSession` connects to the `InteractiveRaptorEngine`.
6.  **Semantic Zooming:** When the user clicks "Zoom In", `InteractiveSession` updates its `current_level` and filters the nodes displayed on `MatomeCanvas`.
7.  **Refinement:** When the user submits a refinement instruction, `InteractiveSession` calls `InteractiveRaptorEngine.refine_node()`. The engine swaps the strategy to `RefinementStrategy`, regenerates the node, and updates the database. The UI automatically reflects this change via reactive binding.

## 4. Design Architecture

The codebase is structured to reflect the domain concepts and architectural layers.

### 4.1. File Structure

```ascii
src/
├── domain_models/
│   ├── data_schema.py       # Pydantic models: SummaryNode, NodeMetadata, DIKWLevel
│   └── config.py            # Configuration: ProcessingConfig
├── matome/
│   ├── agents/
│   │   ├── summarizer.py    # SummarizationAgent (Context-aware LLM wrapper)
│   │   └── strategies.py    # PromptStrategy Protocol and Implementations
│   ├── engines/
│   │   ├── raptor.py        # Base RaptorEngine (Batch processing logic)
│   │   └── interactive.py   # InteractiveRaptorEngine (Single-node operations)
│   ├── ui/
│   │   ├── canvas.py        # MatomeCanvas (Panel View layout)
│   │   └── session.py       # InteractiveSession (ViewModel state machine)
│   └── utils/
│       └── db.py            # Database utilities (Context Managers, Locking)
```

### 4.2. Key Domain Models

**NodeMetadata**
This Pydantic model is the heart of the DIKW system. It extends the standard metadata with:
- `dikw_level`: An Enum (`WISDOM`, `KNOWLEDGE`, `INFORMATION`, `DATA`) defining the abstraction level.
- `refinement_history`: A list of strings tracking every user instruction applied to the node.
- `is_user_edited`: A boolean flag protecting the node from auto-regeneration.

**PromptStrategy (Protocol)**
This interface defines how the system talks to the LLM.
- `format_prompt(text: str, context: dict) -> str`: Constructs the prompt.
- `parse_output(response: str) -> dict`: Parses the LLM's raw response into structured data (summary text + metadata).

### 4.3. Class Responsibilities

- **InteractiveRaptorEngine:** The "Brain". It manages the lifecycle of the knowledge graph. It handles the complex logic of tree traversal (`get_children`, `get_source_chunks`) and ensures atomic updates to the database during refinement.
- **InteractiveSession:** The "State Keeper". It uses `param` to define reactive properties. It validates user actions (e.g., ensuring a node is selected before refining) and orchestrates the UI flow.
- **MatomeCanvas:** The "Face". It is a declarative layout definition using Panel. It binds to `InteractiveSession` properties, ensuring the UI is always in sync with the state.

## 5. Implementation Plan

The project is divided into 5 sequential development cycles.

### CYCLE 01: Core Refactoring (Strategy Pattern)
**Goal:** Prepare the codebase for polymorphism by decoupling the summarization logic from the agent.
**Features:**
- Define the `PromptStrategy` Protocol in `src/matome/agents/strategies.py`.
- Implement `BaseSummaryStrategy` to encapsulate the existing Chain of Density logic (Cycle 0 behavior).
- Refactor `SummarizationAgent` to accept a strategy instance via dependency injection.
- Update `matome.cli` to use the refactored agent.
**Deliverables:** A refactored `SummarizationAgent` that passes all regression tests.

### CYCLE 02: DIKW Engine Implementation
**Goal:** Implement the logic for Semantic Zooming by creating specific strategies for each DIKW level.
**Features:**
- Define `DIKWLevel` Enum and update `NodeMetadata` in `data_schema.py`.
- Implement `WisdomStrategy`: Enforces <50 char limit and philosophical tone.
- Implement `KnowledgeStrategy`: Focuses on "Why/How" and structural mental models.
- Implement `InformationStrategy`: Focuses on "What" and actionable checklists.
- Update `SummarizationAgent` to handle metadata propagation from strategies.
**Deliverables:** A CLI that can generate summaries in "Wisdom", "Knowledge", or "Information" modes.

### CYCLE 03: Interactive Backend & Concurrency
**Goal:** Enable random-access updates to the knowledge graph and ensure database safety.
**Features:**
- Create `InteractiveRaptorEngine` in `src/matome/engines/interactive.py`.
- Implement `refine_node(node_id, instruction)` method, which uses a new `RefinementStrategy`.
- Audit and update `DiskChunkStore` (and `utils/db.py`) to use context managers for all SQLite connections, ensuring thread safety.
- Implement `get_node` and `update_node` primitives.
**Deliverables:** A backend engine capable of updating a single node's text and metadata without regenerating the tree.

### CYCLE 04: GUI Foundation (MVVM)
**Goal:** Establish the reactive user interface architecture.
**Features:**
- Implement `InteractiveSession` (ViewModel) in `src/matome/ui/session.py` using `param`. Define state variables like `selected_node`, `current_level`, `is_refining`.
- Implement `MatomeCanvas` (View) in `src/matome/ui/canvas.py` using `panel`. Create the basic layout (Sidebar, Main Content, Control Panel).
- Bind View components to ViewModel properties.
- Add `serve` command to CLI to launch the Panel server.
**Deliverables:** A running web application where users can view nodes and see details (basic read-only + state foundation).

### CYCLE 05: Semantic Zooming & Traceability
**Goal:** Complete the user experience with full navigation and source verification.
**Features:**
- Implement traversal logic in `InteractiveRaptorEngine`: `get_children(node)` and `get_source_chunks(node)`.
- Implement "Zoom In/Out" logic in `InteractiveSession` (managing a breadcrumb stack).
- Add "Breadcrumbs" component to `MatomeCanvas`.
- Implement "View Source" modal in UI to display original text chunks.
- Apply final CSS styling for a polished look.
**Deliverables:** The complete Matome 2.0 system with all specified features.

## 6. Test Strategy

Testing is integrated into every cycle to ensure robustness.

### Cycle 01 Testing
- **Unit Tests:** Verify that `BaseSummaryStrategy` correctly formats prompts and parses responses. Mock the `SummarizationAgent` to ensure it delegates calls to the strategy.
- **Regression Tests:** Run the full summarization pipeline on a known text and compare the output with Cycle 0 baseline to ensure no functionality is lost.

### Cycle 02 Testing
- **Unit Tests:** Test each new strategy (`Wisdom`, `Knowledge`, `Info`) in isolation. Verify that `WisdomStrategy` produces output < 50 chars. Verify `KnowledgeStrategy` output structure.
- **Integration Tests:** Run the pipeline with `--mode wisdom` and verify that the generated nodes in `chunks.db` have `dikw_level="wisdom"` and `dikw_level="knowledge"` respectively.

### Cycle 03 Testing
- **Concurrency Tests:** Create a stress test script that spawns multiple threads. Each thread should attempt to read and write to `chunks.db` simultaneously via `InteractiveRaptorEngine`. Verify that no `database is locked` errors occur.
- **Functional Tests:** Test `refine_node`. Create a node, refine it with an instruction, and assert that the text has changed and `refinement_history` has length 1.

### Cycle 04 Testing
- **ViewModel Tests:** Test `InteractiveSession` logic without the GUI. Call `select_node` and assert `selected_node` is updated. Call `submit_refinement` and assert the engine method is called.
- **UI Smoke Tests:** Launch the `panel serve` process in a test harness. Verify that the server starts and returns a 200 OK response.

### Cycle 05 Testing
- **Traversal Tests:** Unit test `get_source_chunks`. Create a mock tree structure and verify that the method correctly identifies all leaf nodes (Data) for a given parent.
- **End-to-End (E2E) Tests:** Define a full user scenario (Load -> Zoom -> Refine -> Trace). Execute this manually or via a browser automation tool (like Playwright) to verify the "Happy Path".
