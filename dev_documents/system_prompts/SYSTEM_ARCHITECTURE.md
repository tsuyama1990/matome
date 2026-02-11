# System Architecture: Matome 2.0 "Knowledge Installation"

## 1. Summary

The **Matome 2.0 "Knowledge Installation"** project represents a significant evolutionary leap from the original static summarization tool. While the previous iteration focused on the automated compression of text into summaries using the RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) methodology, Matome 2.0 shifts the paradigm towards **interactive knowledge acquisition**. The core philosophy driving this update is "Semantic Zooming"—a user experience capability that allows users to traverse the hierarchy of information abstraction seamlessly, moving from high-level wisdom down to raw data evidence and back again.

In the information age, users are drowning in data but starving for wisdom. Traditional summarization tools often produce a "wall of text" that, while shorter than the original, still requires significant cognitive load to process. Matome 2.0 addresses this by restructuring the output into a **DIKW (Data, Information, Knowledge, Wisdom)** hierarchy. This structure is not just a method of organization but a cognitive scaffold that mirrors how human experts internalize complex subjects. By presenting the "Wisdom" (the core philosophical insight) first, the system aligns with the user's need for immediate understanding (the "Aha!" moment). From there, the user can "zoom in" to the "Knowledge" layer to understand the supporting structures and mental models, further down to the "Information" layer for actionable checklists, and finally to the "Data" layer to verify the raw source text.

Technically, this transformation requires a departure from a purely batch-oriented command-line interface (CLI) to a rich, interactive Graphical User Interface (GUI) built with **Panel**. The system will no longer just "run and finish"; it will maintain a stateful session where users can critique, refine, and rewrite specific nodes of the knowledge tree. This "Human-in-the-Loop" approach ensures that the final knowledge base is not just an AI artifact but a personalized mental model verified and honed by the user.

To support this, the underlying architecture must evolve. The monolithic `SummarizationAgent` will be refactored to use a **Prompt Strategy Pattern**, allowing for dynamic switching of generation logic based on the target DIKW level. The database layer, powered by SQLite, will be fortified to handle concurrent access from both the generation engine and the interactive UI, ensuring data integrity during real-time refinements. The result will be a robust, extensible platform that transforms the passive act of reading into an active process of "installing" knowledge into the user's mind.

This project is not merely an update; it is a redefinition of the tool's purpose. It transitions Matome from a "Text Summarizer" to a "Cognitive Augmentation Tool." The success of this system will be measured not just by the accuracy of its summaries, but by the speed and depth of the user's understanding of new material.

## 2. System Design Objectives

### 2.1. Semantic Zooming (The DIKW Hierarchy)
The primary design objective is to successfully implement the **Semantic Zooming** capability. This requires the system to rigorously classify and generate content according to the DIKW hierarchy.
-   **Wisdom (Level 1)**: The system must distill the entire context into a single, profound truth or aphorism (20-40 characters). This is the highest level of abstraction, designed to be memorable and impactful.
-   **Knowledge (Level 2)**: The system must explain the "Why" and "How" behind the Wisdom. It should identify frameworks, mechanisms, and structural logic rather than just listing facts.
-   **Information (Level 3)**: The system must convert Knowledge into "Action." This layer provides checklists, rules, and step-by-step guides that are immediately applicable by the user.
-   **Data (Level 4)**: The system must maintain traceability to the original text chunks, serving as the evidence layer.

### 2.2. Interactive Refinement (Human-in-the-Loop)
Unlike the "fire and forget" nature of the previous CLI, Matome 2.0 must support **Interactive Refinement**. Users must be able to challenge the AI's interpretation. If a user feels a "Knowledge" node is too abstract, they should be able to ask the system to "rewrite this with a concrete example." This requires:
-   **State Management**: The system must track which nodes are being edited.
-   **Granular Updates**: The ability to re-generate a single node (and potentially propagate changes) without re-processing the entire tree.
-   **Persistence**: Changes made in the GUI must be saved to the database immediately.

### 2.3. Architectural Decoupling
To maintain maintainability and testability, the system architecture must be strictly decoupled.
-   **Logic vs. Presentation**: The core RAPTOR logic and the Panel GUI must be separate. The GUI should interact with the engine via a well-defined controller interface (`InteractiveRaptorEngine`), never directly with the raw database logic or LLM clients.
-   **Engine vs. Strategy**: The summarization logic should be extracted from the engine. The engine handles the *process* (tree traversal, clustering), while the `PromptStrategy` handles the *content* (what prompt to use for a specific DIKW level).

### 2.4. Concurrency and Data Integrity
With the introduction of an interactive UI, the system moves from a single-threaded batch process to a potentially multi-threaded environment where the UI thread reads data while background threads might be updating it.
-   **SQLite Concurrency**: The `DiskChunkStore` must be enhanced to use SQLite's WAL (Write-Ahead Logging) mode and proper transaction management to prevent database locks and corruption.
-   **Thread Safety**: Access to shared resources must be managed to prevent race conditions.

### 2.5. Extensibility
The system should be designed with future growth in mind. The `PromptStrategy` pattern allows for easy addition of new summarization styles (e.g., "Academic," "Creative," "Technical") without modifying the core engine. The node metadata schema should be flexible enough to support future attributes without requiring database schema migrations.

## 3. System Architecture

The system architecture of Matome 2.0 is built around a clear separation of concerns, utilizing a Model-View-ViewModel (MVVM) pattern for the frontend and a Layered Architecture for the backend.

### 3.1. Components

1.  **Presentation Layer (Panel GUI)**
    -   **Matome Canvas**: The main entry point for the user. It visualizes the DIKW tree.
    -   **Interactive Views**: Components for displaying Wisdom, Knowledge, and Information nodes.
    -   **Chat Interface**: A dedicated panel for users to send refinement instructions to the engine.

2.  **Application Logic Layer (ViewModel)**
    -   **InteractiveSession**: This class acts as the ViewModel. It holds the state of the current session (selected node, current view level, user input) and binds these states to the UI components using the `param` library. It bridges the gap between the GUI and the backend engine.

3.  **Domain Logic Layer (The Engine)**
    -   **InteractiveRaptorEngine**: A wrapper around the core logic specifically designed for the interactive use case. It exposes methods like `refine_node(node_id, instruction)` and `get_tree_structure()`. It orchestrates the flow of data.
    -   **RaptorEngine (Core)**: The existing batch processing engine, modified to utilize strategies.

4.  **Strategy Layer**
    -   **PromptStrategy**: An interface defining how prompts are constructed.
    -   **WisdomStrategy / KnowledgeStrategy / ActionStrategy**: Concrete implementations that contain the specific prompt engineering logic for each DIKW level.

5.  **Data Persistence Layer**
    -   **DiskChunkStore**: The interface to the SQLite database (`chunks.db`). It handles CRUD operations for `SummaryNode` and `Chunk`. It implements context managers for transaction safety.

### 3.2. Data Flow

1.  **Ingestion**: Raw text is chunked and stored in `DiskChunkStore`.
2.  **Generation**: The `RaptorEngine` retrieves chunks, clusters them, and uses the appropriate `PromptStrategy` to generate summaries.
3.  **Visualization**: The `InteractiveSession` queries the `DiskChunkStore` via the `InteractiveRaptorEngine` to build the visualization tree.
4.  **Refinement**: The user selects a node and sends an instruction. The `InteractiveSession` passes this to the `InteractiveRaptorEngine`.
5.  **Update**: The engine calls the LLM with the instruction, updates the `SummaryNode`, and persists it to `DiskChunkStore`. The UI automatically refreshes via reactive bindings.

### 3.3. Architectural Diagram

```mermaid
graph TD
    User[User] -->|Interacts| GUI[Panel GUI (View)]
    GUI <-->|Binds| VM[InteractiveSession (ViewModel)]
    VM -->|Calls| Controller[InteractiveRaptorEngine]

    subgraph "Core Engine"
        Controller -->|Uses| Store[DiskChunkStore (SQLite)]
        Controller -->|Uses| Agent[SummarizationAgent]
        Agent -->|Uses| Strategy[PromptStrategy Interface]

        Strategy <|-- W[WisdomStrategy]
        Strategy <|-- K[KnowledgeStrategy]
        Strategy <|-- A[ActionStrategy]
    end

    subgraph "External"
        LLM[OpenAI / LLM API]
    end

    Agent -->|API Call| LLM
```

## 4. Design Architecture

The design architecture focuses on the file structure and the strict schema definitions that underpin the system's reliability.

### 4.1. File Structure

```ascii
src/matome/
├── agents/
│   ├── __init__.py
│   ├── summarizer.py       # Enhanced SummarizationAgent
│   └── strategies.py       # New: PromptStrategy definitions
├── engines/
│   ├── __init__.py
│   ├── raptor.py           # Core Batch Engine
│   └── interactive.py      # New: InteractiveRaptorEngine
├── interface/
│   ├── __init__.py
│   ├── app.py              # Panel App Entry Point
│   ├── session.py          # ViewModel (InteractiveSession)
│   └── components/         # UI Components
│       ├── __init__.py
│       ├── canvas.py
│       └── chat.py
├── utils/
│   ├── __init__.py
│   └── store.py            # Enhanced DiskChunkStore
└── cli.py

src/domain_models/
├── __init__.py
├── manifest.py             # SummaryNode, DocumentTree
└── metadata.py             # New: NodeMetadata, DIKWLevel
```

### 4.2. Class and Data Design

The system relies heavily on Pydantic for data validation and schema enforcement.

#### 4.2.1. Node Metadata (New)
To support the DIKW hierarchy without altering the database schema significantly, we utilize the `metadata` field of the `SummaryNode`.

```python
class DIKWLevel(str, Enum):
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"

class NodeMetadata(BaseModel):
    dikw_level: DIKWLevel
    is_user_edited: bool = False
    refinement_history: List[str] = Field(default_factory=list)
    # ... other existing metadata fields
```

#### 4.2.2. Prompt Strategy Interface
To decouple the prompt logic from the execution logic.

```python
class PromptStrategy(Protocol):
    def create_prompt(self, context_chunks: List[str], current_level: int) -> str:
        ...

    def parse_output(self, llm_output: str) -> str:
        ...
```

#### 4.2.3. Interactive Session (ViewModel)
To manage the state of the UI.

```python
class InteractiveSession(param.Parameterized):
    selected_node_id = param.String()
    current_view_level = param.Selector(objects=DIKWLevel)
    user_input = param.String()
    is_processing = param.Boolean(default=False)

    def on_node_select(self, event): ...
    def submit_refinement(self): ...
```

## 5. Implementation Plan

The implementation is divided into 5 sequential cycles, each building upon the previous one to ensure a stable and verifiable progression.

### Cycle 01: Core Refactoring & DIKW Metadata
**Goal**: Establish the data structures and interfaces required for the new DIKW logic without breaking existing functionality.
-   **Refactoring**: Identify the hardcoded prompt logic in `SummarizationAgent` and prepare it for extraction.
-   **Data Modeling**: Implement the `NodeMetadata` and `DIKWLevel` Pydantic models in `src/domain_models/metadata.py`. Update `SummaryNode` in `src/domain_models/manifest.py` to enforce the use of this new metadata schema.
-   **Interface Definition**: Define the `PromptStrategy` protocol in `src/matome/agents/strategies.py`.
-   **Migration Logic**: Create a utility to verify that existing nodes in the DB (if any) can gracefully handle the new metadata structure (e.g., defaulting to a generic level).
-   **Verification**: Ensure that the CLI still runs with the new data models, even if the logic hasn't changed yet.

### Cycle 02: DIKW Generation Engine
**Goal**: Implement the "Semantic Zooming" logic by creating specific Prompt Strategies for each DIKW level.
-   **Strategy Implementation**: Create `WisdomStrategy`, `KnowledgeStrategy`, and `ActionStrategy` in `src/matome/agents/strategies.py`.
    -   `WisdomStrategy`: Engineered to produce abstract, philosophical aphorisms (max 40 chars).
    -   `KnowledgeStrategy`: Engineered to extract structural logic and frameworks.
    -   `ActionStrategy`: Engineered to produce concrete checklists and to-dos.
-   **Agent Integration**: Modify `SummarizationAgent` to accept a `PromptStrategy` factory or selector.
-   **Engine Update**: Update `RaptorEngine` to assign the correct strategy based on the tree depth (Level 0 = Action/Data, Intermediate = Knowledge, Root = Wisdom).
-   **Verification**: Run the batch process and verify that the generated summaries match the DIKW definitions.

### Cycle 03: Interactive Engine & Concurrency
**Goal**: Prepare the backend for the interactive GUI by creating a dedicated controller and ensuring thread safety.
-   **Interactive Controller**: Implement `InteractiveRaptorEngine` in `src/matome/engines/interactive.py`. This class will handle requests like `get_node(id)`, `get_children(id)`, and `refine_node(id, instruction)`.
-   **Concurrency Hardening**: Refactor `DiskChunkStore` to use context managers (`with self.get_session() as session:`) for all DB operations. Enable WAL mode for SQLite to allow simultaneous readers and writers.
-   **Locking Mechanism**: Implement a simple locking mechanism (if needed) to prevent the same node from being edited by multiple processes simultaneously (though primarily single-user, this is good practice).
-   **Verification**: Create integration tests that simulate concurrent read/write operations to ensure no database locks or corruption occur.

### Cycle 04: GUI Foundation (MVVM)
**Goal**: Build the visual framework of the application using Panel and the MVVM pattern.
-   **ViewModel Implementation**: Create `InteractiveSession` in `src/matome/interface/session.py` using `param`. Define all reactive parameters and state variables.
-   **Canvas Layout**: Create the main application shell in `src/matome/interface/app.py`. Implement the basic layout: a navigation area (Tree/Pyramid view) and a content area.
-   **Component Design**: create reusable UI components for displaying nodes (`components/canvas.py`).
-   **Connection**: Wire the `InteractiveSession` to the `InteractiveRaptorEngine` (read-only for now).
-   **Verification**: Launch the Panel app and verify that it can display the tree structure generated in Cycle 02.

### Cycle 05: Semantic Zooming & Final Polish
**Goal**: Complete the interactive loop and polish the user experience.
-   **Refinement Logic**: Connect the "Chat" interface in the GUI to the `refine_node` method in the backend. Implement the logic to send the user's instruction + the current node text to the LLM and update the result.
-   **Zoom Navigation**: Implement the "Drill-down" UI logic. Clicking a Wisdom node should reveal its child Knowledge nodes. Clicking a Knowledge node should reveal Action nodes.
-   **Source Traceability**: Implement the "Show Source" feature that links Action/Data nodes back to the original text chunks.
-   **Final UAT**: comprehensive user acceptance testing based on the defined scenarios.
-   **Documentation**: Finalize README and usage guides.

## 6. Test Strategy

### Cycle 01 Testing Strategy
-   **Unit Tests**:
    -   Test `NodeMetadata` validation. Ensure `dikw_level` rejects invalid strings.
    -   Test `SummaryNode` instantiation with the new metadata.
    -   Test that `PromptStrategy` protocol is correctly defined (using static analysis/mypy).
-   **Regression Tests**:
    -   Run existing CLI tests to ensure the refactoring didn't break basic ingestion and chunking.

### Cycle 02 Testing Strategy
-   **Unit Tests**:
    -   Test each Strategy (`WisdomStrategy`, etc.) in isolation. Mock the LLM and verify that the `create_prompt` method generates the expected string format.
    -   Test the parsing logic of each strategy.
-   **Integration Tests**:
    -   Run a small scale RAPTOR process (e.g., with a dummy text). Inspect the output database. Verify that the Root node has `dikw_level="wisdom"` and leaf summaries have `dikw_level="information"`.
    -   **Prompt Evaluation**: (Manual/Semi-automated) Review generated Wisdom nodes. Are they truly short (20-40 chars)? Are Knowledge nodes structural?

### Cycle 03 Testing Strategy
-   **Concurrency Tests**:
    -   Create a test script that spawns multiple threads. One thread constantly reads the tree structure. Another thread randomly updates nodes. Verify that no `sqlite3.OperationalError: database is locked` exceptions are raised.
    -   Verify that data written by the writer thread is eventually visible to the reader thread.
-   **Controller Tests**:
    -   Unit test `InteractiveRaptorEngine`. Mock the `SummarizationAgent`. Call `refine_node` and assert that the `DiskChunkStore.update_node` was called with the new text and `is_user_edited=True`.

### Cycle 04 Testing Strategy
-   **UI Unit Tests**:
    -   Test `InteractiveSession` (ViewModel) logic. Trigger `on_node_select` and verify that `selected_node_id` changes.
    -   Test that updating `user_input` in the ViewModel triggers the appropriate watchers.
-   **Visual Verification**:
    -   Since automated UI testing for Panel can be complex, rely on manual verification that the components render correctly and the initial tree is loaded.
    -   Verify that the "Wisdom" view only shows the root node initially.

### Cycle 05 Testing Strategy
-   **End-to-End (E2E) Tests**:
    -   Full walkthrough of the User Scenarios.
    -   **Scenario A (Zooming)**: Verify smooth transition from Level 1 to Level 3.
    -   **Scenario B (Refinement)**: Edit a node, save it, restart the app, and verify the change persists.
    -   **Scenario C (Traceability)**: Verify that leaf nodes correctly display the original source chunks.
-   **Performance Testing**:
    -   Measure the latency of the `refine_node` operation. It should be within acceptable limits (LLM latency + overhead).
    -   Ensure the UI remains responsive during generation.
