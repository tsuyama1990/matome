# System Architecture: Matome 2.0 - Knowledge Installation

## 1. Summary

The Matome 2.0 "Knowledge Installation" project represents a significant evolution from the existing static summarization command-line interface (CLI) to a dynamic, interactive graphical user interface (GUI). The core philosophy driving this transformation is the concept of "Knowledge Installation"—the idea that true understanding comes not from passive consumption of summaries, but from active engagement with information at varying levels of abstraction. The system is designed to facilitate "Semantic Zooming," allowing users to traverse a Data-Information-Knowledge-Wisdom (DIKW) hierarchy, moving seamlessly from high-level philosophical insights down to the raw data that supports them.

The original system provided a robust mechanism for recursive summarization using the RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) algorithm. However, its output was static—a fixed tree of summaries that, while structured, did not adapt to the user's specific mental model or learning pace. Matome 2.0 addresses this limitation by introducing an interactive layer that empowers users to refine, restructure, and query the knowledge graph in real-time. This shift requires a fundamental re-architecture of the backend to support random access, partial updates, and concurrency, alongside the development of a reactive frontend capable of visualizing complex hierarchical data.

At the heart of the new system is the "DIKW-Reverse Logic" engine. Unlike traditional summarization which merely compresses text, this engine explicitly targets different levels of the DIKW pyramid. Level 1 (Wisdom) distills content into context-free aphorisms and core truths. Level 2 (Knowledge) articulates the logical frameworks and mental models that underpin these truths. Level 3 (Information) provides actionable steps and checklists derived from the knowledge. Finally, Level 4 (Data) anchors everything in the original source text. This structured approach ensures that users can obtain a "Grok" moment—an intuitive grasp of the core message—within seconds, while retaining the ability to verify and explore the supporting details.

The transition also involves a move towards a more modular and extensible codebase. The monolithic summarization logic is being refactored into a Strategy Pattern, allowing different prompt strategies to be swapped dynamically. This is crucial for the interactive refinement feature, where a user might ask to "rewrite this node for a 5-year-old" or "make this more professional," requiring a different prompting strategy than the initial batch generation. Furthermore, the system adopts an MVVM (Model-View-ViewModel) architecture for the GUI, using the Panel library to create a responsive and maintainable user interface that strictly separates the presentation logic from the underlying data models.

In essence, Matome 2.0 is not just a summarizer; it is a tool for thought. It transforms the passive act of reading into an active process of knowledge construction, enabling users to internalize complex information more effectively than ever before. By combining advanced NLP techniques with intuitive UI design, the system aims to bridge the gap between raw data and human wisdom.

## 2. System Design Objectives

The design of Matome 2.0 is guided by several critical objectives, constraints, and success criteria that ensure the final product meets the high standards of "Knowledge Installation."

### 2.1. Primary Goals

**1. Semantic Zooming Capability:**
The primary goal is to enable users to navigate information vertically through levels of abstraction. The system must support instant transitions between "Wisdom" (L1), "Knowledge" (L2), "Information" (L3), and "Data" (L4). This requires a backend capable of retrieving and serving specific nodes and their children with low latency, and a frontend that visualizes these relationships intuitively. The "Zooming" metaphor is not just visual but conceptual; the content itself must change in nature—from abstract principles to concrete facts—as the user zooms in.

**2. Interactive Refinement (The "Human-in-the-Loop"):**
Knowledge is personal. What resonates with one user may be confusing to another. Therefore, the system must allow users to intervene in the summarization process. Users must be able to select any node in the DIKW tree and provide natural language instructions to refine it. The system must process these refinements in real-time, updating only the affected parts of the tree (and potentially propagating changes) without requiring a full regeneration of the entire document. This "partial update" capability is a significant architectural challenge that distinguishes Matome 2.0 from its predecessor.

**3. Architectural Modularity and Extensibility:**
To support the diverse needs of interactive refinement and potential future expansions (e.g., different languages, domain-specific models), the system must be highly modular. Hard-coded prompts and monolithic functions are strictly prohibited. The adoption of the Strategy Pattern for prompt generation and the separation of the interactive engine from the batch engine are key steps to achieving this. The system should be able to accommodate new summarization strategies or clustering algorithms with minimal disruption to the core codebase.

**4. Data Integrity and Traceability:**
In the era of LLM hallucinations, trust is paramount. The system must maintain strict traceability from the highest-level wisdom down to the original text chunks. Every node must maintain metadata linking it to its children and, ultimately, the source. The "Source Verification" feature is not an add-on but a core requirement; users must always be able to see the evidence backing up an AI-generated claim.

### 2.2. Constraints

-   **Latency:** Interactive operations (e.g., node refinement) must complete within a reasonable timeframe (seconds, not minutes) to maintain flow.
-   **Concurrency:** The system must handle simultaneous read/write access to the local SQLite database (`chunks.db`) from both the background batch processes and the interactive GUI sessions without data corruption.
-   **Dependencies:** The solution must be implemented in Python 3.11+ using the specified stack (LangChain, Panel, Pydantic, etc.) and must be deployable as a local application.
-   **Cost:** While using powerful models (GPT-4o), the system should optimize token usage where possible, avoiding unnecessary regeneration of the entire tree when only a branch is modified.

### 2.3. Success Criteria

-   **DIKW Fidelity:** The generated "Wisdom" nodes must be abstract and universally applicable, while "Action" nodes must be concrete and executable.
-   **Responsiveness:** The GUI should render the initial tree immediately upon load and reflect updates dynamically.
-   **Stability:** The system must pass all regression tests for the existing CLI functionality while introducing the new interactive features.
-   **User Experience:** A user should be able to reach an "Aha!" moment regarding a complex text within 5 minutes of using the tool, as measured by the UAT scenarios.

## 3. System Architecture

The Matome 2.0 architecture is a layered system designed to separate concerns between data storage, processing logic, and user interaction. It leverages a local vector store and relational database for persistence, an extensible engine for logic, and a reactive frontend.

### 3.1. High-Level Components

1.  **Presentation Layer (Matome Canvas):**
    -   Built with **Panel**.
    -   Implements the **MVVM** pattern.
    -   **View:** Visualization components (Tree view, Chat interface, Detail view).
    -   **ViewModel:** `InteractiveSession` manages the state (selected node, edit mode, chat history) and exposes reactive parameters.

2.  **Application Layer (Interactive Engine):**
    -   **InteractiveRaptorEngine:** A wrapper/controller that orchestrates interactions. It bridges the GUI and the core logic.
    -   **Responsibilities:** Handling "Refine Node" requests, managing DB transactions, and invoking the appropriate agents.
    -   **Concurrency:** Manages access to the underlying storage to prevent race conditions.

3.  **Domain Logic Layer (Agents & Strategies):**
    -   **SummarizationAgent:** The core worker interacting with the LLM.
    -   **PromptStrategy:** A pluggable interface defining how to generate prompts for different DIKW levels (Wisdom, Knowledge, Action) and refinement tasks.
    -   **GMMClusterer / SemanticChunker:** Existing components for structuring the text.

4.  **Data Persistence Layer:**
    -   **DiskChunkStore:** An abstraction over SQLite (`chunks.db`) and the Vector Store.
    -   **SummaryNode / Chunk:** Pydantic models defining the data schema, now enhanced with DIKW metadata.

### 3.2. Data Flow

1.  **Initial Ingestion (Batch):**
    `CLI` -> `RaptorEngine` -> `JapaneseSemanticChunker` -> `DiskChunkStore` (Save Chunks) -> `GMMClusterer` -> `SummarizationAgent` (with `DIKWStrategy`) -> `DiskChunkStore` (Save Nodes).

2.  **Interactive Zooming (Read):**
    `Panel View` -> `InteractiveSession` (ViewModel) -> `InteractiveRaptorEngine` -> `DiskChunkStore` -> `Return SummaryNode` -> `View Update`.

3.  **Node Refinement (Write):**
    `Panel Chat` -> `InteractiveSession` -> `InteractiveRaptorEngine.refine_node(node_id, instruction)` -> `SummarizationAgent` (with `RefinementStrategy`) -> `LLM` -> `New Text` -> `DiskChunkStore` (Update) -> `Signal View Update`.

### 3.3. Architecture Diagram

```mermaid
graph TD
    subgraph Frontend [Presentation Layer - Matome Canvas]
        View[Panel View]
        ViewModel[InteractiveSession (ViewModel)]
        View <--> ViewModel
    end

    subgraph Backend [Application Layer]
        Controller[InteractiveRaptorEngine]
        ViewModel <--> Controller
    end

    subgraph Core [Domain Logic Layer]
        Agent[SummarizationAgent]
        Strategy[PromptStrategy Interface]
        Wisdom[WisdomStrategy]
        Knowledge[KnowledgeStrategy]
        Action[ActionStrategy]
        Refine[RefinementStrategy]

        Controller --> Agent
        Agent --> Strategy
        Strategy <|-- Wisdom
        Strategy <|-- Knowledge
        Strategy <|-- Action
        Strategy <|-- Refine
    end

    subgraph Storage [Data Persistence Layer]
        Store[DiskChunkStore]
        DB[(SQLite / VectorDB)]

        Controller --> Store
        Agent --> Store
        Store <--> DB
    end

    %% Data Flow for Refinement
    ViewModel -- "Refine(ID, Instruction)" --> Controller
    Controller -- "Invoke(Node, Instruction)" --> Agent
    Agent -- "Generate Prompt" --> Refine
    Refine -- "Prompt" --> Agent
    Agent -- "LLM Call" --> Agent
    Agent -- "Update Node" --> Store
```

## 4. Design Architecture

This section details the concrete implementation structure, file organization, and key data models. The design strictly adheres to Pydantic for data validation and schema definition.

### 4.1. File Structure

```ascii
src/
├── domain_models/
│   ├── __init__.py
│   ├── config.py              # Configuration models (Pydantic)
│   ├── constants.py           # System constants
│   ├── manifest.py            # Core Data Models (SummaryNode, Chunk)
│   ├── types.py               # Type aliases
│   └── verification.py        # Verification models
├── matome/
│   ├── __init__.py
│   ├── cli.py                 # CLI Entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract Agent definitions
│   │   ├── summarization.py   # SummarizationAgent implementation
│   │   └── strategies.py      # PromptStrategy implementations (NEW)
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── raptor.py          # Batch RaptorEngine
│   │   ├── interactive.py     # InteractiveRaptorEngine (NEW)
│   │   ├── semantic_chunker.py
│   │   └── clusterer.py
│   ├── interface/             # GUI Package (NEW)
│   │   ├── __init__.py
│   │   ├── app.py             # Panel App Entry point
│   │   ├── components.py      # Reusable UI components
│   │   └── viewmodel.py       # InteractiveSession (ViewModel)
│   └── utils/
│       ├── __init__.py
│       └── logging.py
```

### 4.2. Key Components & Class Definitions

**1. `PromptStrategy` (Protocol)**
Located in `src/matome/agents/strategies.py`.
Defines the contract for prompt generation.
```python
class PromptStrategy(Protocol):
    def create_prompt(self, text: str, context: dict) -> str: ...
```
Concrete implementations: `DIKWHierarchyStrategy`, `RefinementStrategy`, `SimpleSummaryStrategy`.

**2. `SummaryNode` (Enhanced)**
Located in `src/domain_models/manifest.py`.
The `metadata` field is now strictly typed or validated to contain:
- `dikw_level`: Enum (`Wisdom`, `Knowledge`, `Information`, `Data`)
- `is_user_edited`: boolean
- `refinement_history`: List of strings (audit trail)

**3. `InteractiveRaptorEngine`**
Located in `src/matome/engines/interactive.py`.
API methods:
- `get_node(node_id) -> SummaryNode`
- `get_children(node_id) -> List[SummaryNode]`
- `refine_node(node_id, instruction) -> SummaryNode`
- `verify_source(node_id) -> SourceChunks`

**4. `InteractiveSession` (ViewModel)**
Located in `src/matome/interface/viewmodel.py`.
Uses `param` library for reactivity.
- `selected_node`: param.ClassSelector(SummaryNode)
- `chat_history`: param.List()
- `is_processing`: param.Boolean()
- `user_input`: param.String()

### 4.3. Data Models and Invariants

-   **Immutability of IDs:** Once a node is created, its ID remains constant to preserve references in the vector store and parent links, even if its content is refined.
-   **Traceability:** Every `SummaryNode` must have a non-empty `children_indices` list (unless it's a leaf/chunk), ensuring the path to source data is never broken.
-   **Type Safety:** All data exchanges between layers are wrapped in Pydantic models to ensure runtime type checking and prevent data corruption.

## 5. Implementation Plan

The project is divided into 5 sequential cycles. Each cycle builds upon the previous one, ensuring a stable and testable increment at each stage.

### CYCLE 01: Core Refactoring & Metadata Standardization
**Objective:** Prepare the foundation by refactoring the prompt logic and standardizing metadata without breaking existing functionality.
-   **Tasks:**
    -   Define the `PromptStrategy` protocol in `src/matome/agents/strategies.py`.
    -   Move existing hardcoded prompts into a default `SimpleSummaryStrategy`.
    -   Update `SummarizationAgent` to accept a strategy instance.
    -   Update `SummaryNode` definition (or validation logic) to enforce `dikw_level` and `refinement_history` in metadata.
    -   **Constraint:** The existing CLI `matome run` must produce the exact same output (functionally) as before.

### CYCLE 02: DIKW Generation Engine
**Objective:** Implement the "Logic" of Semantic Zooming.
-   **Tasks:**
    -   Implement specific strategies: `WisdomStrategy`, `KnowledgeStrategy`, `ActionStrategy`.
    -   Modify `RaptorEngine` (or create a configuration for it) to apply these strategies at appropriate tree levels (e.g., L1=Wisdom, L2=Knowledge).
    -   Implement the mapping logic: Tree Level -> Prompt Strategy.
    -   **Deliverable:** A batch process that generates a tree where the root is abstract wisdom and leaves are concrete data.

### CYCLE 03: Interactive Engine & Concurrency
**Objective:** Build the "Controller" capable of handling granular updates and safe DB access.
-   **Tasks:**
    -   Implement `InteractiveRaptorEngine` in `src/matome/engines/interactive.py`.
    -   Implement `refine_node` method: Fetch node -> Apply `RefinementStrategy` -> Update DB.
    -   Enhance `DiskChunkStore` to use context managers (`with store.session():`) for thread-safe SQLite transactions.
    -   **Deliverable:** A backend API (Python class) that allows specific nodes to be rewritten programmatically.

### CYCLE 04: GUI Foundation (MVVM)
**Objective:** Establish the "View" and "ViewModel" using Panel.
-   **Tasks:**
    -   Set up the Panel application structure in `src/matome/interface/`.
    -   Implement `InteractiveSession` (ViewModel) using `param`.
    -   Create basic View components: `TreeNavigator` and `NodeDetailView`.
    -   Connect the View to the `InteractiveRaptorEngine` (Read-only for now).
    -   **Deliverable:** A runnable GUI that displays the generated DIKW tree and allows navigation.

### CYCLE 05: Semantic Zooming & Refinement (Final Polish)
**Objective:** Complete the "Experience" with interactive editing and source verification.
-   **Tasks:**
    -   Implement the "Refinement Chat" component in the GUI.
    -   Connect the chat input to `InteractiveSession.refine_node`.
    -   Implement `SourceViewer` to display original text chunks linked to a node.
    -   Finalize "Source Verification" logic.
    -   **Deliverable:** The complete Matome 2.0 system.

## 6. Test Strategy

Testing is integral to the AC-CDD process. Each cycle has a specific testing focus.

### 6.1. General Testing Principles
-   **Unit Tests:** Verify individual components (Strategies, Agent, Store) in isolation using mocks.
-   **Integration Tests:** Verify the interaction between the Engine and the Database.
-   **UAT (User Acceptance Tests):** Verify the end-to-end user experience using Jupyter Notebooks.

### 6.2. Cycle-Specific Strategies

**Cycle 01 (Refactoring):**
-   **Regression Testing:** The primary goal is to ensure NO regression. The existing test suite must pass 100%.
-   **Strategy Tests:** specific unit tests for `SimpleSummaryStrategy` to ensure it generates expected prompts.
-   **Metadata Tests:** Verify that `SummaryNode` correctly validates and serializes the new metadata fields.

**Cycle 02 (DIKW Logic):**
-   **Content Verification:** Manually (or via LLM evaluation) verify that L1 nodes are indeed "abstract" and L3 nodes are "concrete".
-   **Integration Tests:** Run the full `RaptorEngine` on a sample text and check the `dikw_level` distribution in the resulting database.

**Cycle 03 (Interactive Engine):**
-   **Concurrency Tests:** Simulate multiple threads trying to read/write to `DiskChunkStore` simultaneously to ensure no `database is locked` errors occur.
-   **State Tests:** Verify that `refine_node` updates the specific node but leaves its children and neighbors key intact.

**Cycle 04 (GUI Foundation):**
-   **Component Tests:** Verify that Panel components render without errors.
-   **ViewModel Tests:** Unit test `InteractiveSession`—changing a param should trigger the expected callbacks or state changes (mocking the engine).
-   **Launch Test:** Ensure the app launches via `matome canvas` (or similar command) without crashing.

**Cycle 05 (Refinement & Polish):**
-   **E2E UI Tests:** (Manual or scripted) Open the app, click a node, type a refinement, and verify the text updates on screen.
-   **Traceability Tests:** Verify that clicking "Show Source" retrieves the correct chunks from the DB.
-   **Final UAT:** Execute the "Aha! Moment" scenario fully.
