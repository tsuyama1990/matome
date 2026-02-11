# System Architecture: Matome 2.0 "Knowledge Installation" Update

## 1. Summary

Matome 2.0 represents a significant evolutionary leap from the original Matome project, transforming it from a static, CLI-based summarization utility into a dynamic, interactive "Knowledge Installation" platform. The core philosophy driving this update is the shift from passive information consumption to active knowledge construction. In the era of information overload, merely condensing text is insufficient; users need tools that allow them to restructure information into mental models that resonate with their own cognitive frameworks. Matome 2.0 addresses this by introducing "Semantic Zooming" based on the DIKW (Data, Information, Knowledge, Wisdom) hierarchy, and providing an interactive "Matome Canvas" for exploring and refining this hierarchy.

The original Matome system successfully implemented the Recursive Abstractive Processing (RAPTOR) algorithm, enabling it to digest large documents into hierarchical summaries. However, the output was static—a fixed tree of summaries that, while structured, did not necessarily align with the user's specific learning goals or prior knowledge. If a summary was too abstract, the user couldn't easily drill down. If it was too detailed, they couldn't zoom out. Furthermore, the summarization logic was hard-coded, making it difficult to adapt the system for different types of "understanding" (e.g., philosophical distillation vs. actionable checklists).

Matome 2.0 solves these problems by redefining the summarization process as a "Reverse DIKW" generation. Instead of generic summaries, the system explicitly generates content at four distinct levels of abstraction:
1.  **Wisdom (L1)**: The philosophical core, aphorisms, and high-level insights that represent the "soul" of the content. This is the "Why" and the "So What."
2.  **Knowledge (L2)**: The structural frameworks, mental models, and logical connections that support the wisdom. This explains the "How it works."
3.  **Information (L3)**: Actionable instructions, checklists, and concrete steps derived from the knowledge. This is the "What to do."
4.  **Data (L4)**: The raw textual evidence and original chunks that serve as the ground truth.

To support this new paradigm, the system architecture undergoes a major refactoring. The monolithic `SummarizationAgent` is broken down using the Strategy Pattern, allowing different `PromptStrategy` implementations to be injected for each DIKW level. A new `InteractiveRaptorEngine` is introduced to handle granular, node-level updates without reprocessing the entire tree, enabling a responsive user experience. Finally, a modern GUI built with the Panel library and following the MVVM (Model-View-ViewModel) pattern provides the visual interface for this "Semantic Zooming," allowing users to navigate the pyramid of knowledge and interactively refine nodes via chat.

This transformation positions Matome 2.0 not just as a summarizer, but as a "Thinking Partner" that helps users internalize complex information by letting them manipulate the structure of that information directly. It bridges the gap between raw data and human understanding, ensuring that the "AI" in the loop serves to amplify human cognition rather than replace it.

## 2. System Design Objectives

The design of Matome 2.0 is guided by a set of rigorous objectives and constraints aimed at ensuring the system is not only functional but also scalable, maintainable, and delightful to use.

### Primary Objectives

1.  **Enable Semantic Zooming (The "Google Earth" of Text)**:
    The defining feature of Matome 2.0 is the ability to traverse information vertically. Users must be able to start at the "Wisdom" level to grasp the essence of a document in seconds, and then "zoom in" to the underlying "Knowledge" and "Information" layers as needed. This requires the backend to generate summaries that are not just shorter versions of the text, but qualitatively different representations (abstract vs. concrete, theoretical vs. practical) linked in a coherent hierarchy. The success of this objective is measured by the distinctness of each layer—a Wisdom node must feel philosophical, while an Action node must feel pragmatic.

2.  **Interactive Knowledge Refinement**:
    Static summaries are often "one size fits all." Matome 2.0 aims to make knowledge personal. Users must be able to "talk" to the data. If a "Knowledge" node is too academic, the user should be able to ask the system to "rewrite this for a 5-year-old." This requires an architecture that supports `Single Node Refinement`—the ability to update a specific node in the tree and persist that change without breaking the integrity of the overall structure or requiring a computationally expensive full re-run.

3.  **Strict Data Lineage and Traceability**:
    In the age of AI hallucinations, trust is paramount. Matome 2.0 maintains the rigorous verification standards of its predecessor but enhances accessibility. Every abstract claim in the "Wisdom" or "Knowledge" layers must be traceable back to the "Data" layer (raw text chunks). The UI must provide a "Source Verification" mechanism that allows users to instantly view the original text snippet that generated a specific insight, ensuring that the system's "Wisdom" is grounded in the document's reality.

4.  **Architectural Decoupling for Extensibility**:
    The system must be designed to accommodate future growth. The separation of the summarization logic (via `PromptStrategy`) from the execution engine (`SummarizationAgent`) is critical. This allows developers (and potentially users) to define new types of summary strategies (e.g., "Socratic Questioning," "Debate Mode") without modifying the core engine. Similarly, the GUI must be decoupled from the backend logic using the MVVM pattern, ensuring that changes to the UI do not ripple into the data processing layer, and vice versa.

### Constraints & Technical Considerations

*   **Concurrency & State Management**: The shift from a batch-process CLI to an interactive GUI introduces significant state management challenges. The `chunks.db` (SQLite) must handle concurrent reads (from the UI) and writes (from the refinement engine) robustly. We must implement strict context managers and transaction locking strategies to prevent database corruption or "file locked" errors, especially since SQLite is file-based.
*   **Latency vs. Quality**: Interactive refinement needs to feel responsive. While we cannot control LLM generation time, we must minimize system overhead. This means avoiding unnecessary re-computations. When a node is updated, we should update *only* that node and its direct dependencies, rather than triggering a cascade of updates up the tree unless explicitly requested.
*   **Dependency Management**: The project enforces strict dependency control using `uv` (or standard `pip` with `pyproject.toml`). We must not introduce heavy dependencies unless absolutely necessary. The GUI is built on `Panel` to leverage the existing Python data science ecosystem, avoiding the complexity of a separate JavaScript frontend.

### Success Criteria

*   **User Experience**: A user can load a 100-page book and understand its core message in under 1 minute (Wisdom view), then spend 10 minutes exploring key concepts (Knowledge view), and finally export a checklist (Action view).
*   **Technical Performance**: Single node refinement (excluding LLM inference time) takes less than 500ms for DB updates.
*   **Code Quality**: The codebase maintains a strict separation of concerns, with 100% type coverage (strict `mypy`) and adherence to the MVVM pattern in the GUI.

## 3. System Architecture

The Matome 2.0 architecture is a layered, modular system designed to support both high-throughput batch processing (CLI) and low-latency interactive exploration (GUI). It consists of three primary layers: the **Interface Layer**, the **Application/Control Layer**, and the **Domain/Data Layer**.

### High-Level Components

1.  **Interface Layer (The "Front End")**:
    *   **CLI (`matome.cli`)**: The traditional entry point for batch processing. It orchestrates the full ingestion pipeline: Chunking -> Embedding -> Clustering -> Summarization (DIKW generation). It is optimized for stability and logging.
    *   **GUI (`matome.ui`)**: A web-based interface built with **Panel**. It follows the **MVVM** pattern.
        *   **View**: The layout and widgets (Pyramid Navigation, Chat Box). It observes the ViewModel.
        *   **ViewModel (`InteractiveSession`)**: Holds the session state (current selection, edit history, view mode). It mediates between the View and the Backend.

2.  **Application/Control Layer (The "Brain")**:
    *   **Interactive Raptor Engine (`InteractiveRaptorEngine`)**: A wrapper around the core `RaptorEngine`. It exposes granular methods like `refine_node(node_id, instruction)` and `get_node_lineage(node_id)`. It manages the orchestration of agents for interactive tasks.
    *   **Agents**:
        *   **Summarization Agent**: Now enhanced with injected `PromptStrategy`. It doesn't just "summarize"; it "transforms" text based on the active strategy (Wisdom, Knowledge, Action).
        *   **Verifier Agent**: Ensures the output is faithful to the source.
    *   **Strategies (`src/matome/strategies`)**: Concrete implementations of `PromptStrategy` (e.g., `WisdomStrategy`, `ActionStrategy`) that define the specific prompts and parsing logic for each DIKW level.

3.  **Domain/Data Layer (The "Memory")**:
    *   **DiskChunkStore**: The abstraction over SQLite (`chunks.db`). It handles CRUD operations for `SummaryNode` and `Chunk` objects. In Matome 2.0, it is hardened for concurrent access.
    *   **Domain Models**: Pydantic models defining `SummaryNode`, `NodeMetadata` (updated with DIKW fields), and `VerificationResult`. These are the "lingua franca" of the system.

### Data Flow

1.  **Ingestion (Batch)**: Raw Text -> `SemanticChunker` -> `EmbeddingService` -> `Clustering (GMM)` -> `SummarizationAgent` (using DIKW Strategies) -> `DiskChunkStore`.
2.  **Interaction (Real-time)**: User Input (GUI) -> `InteractiveSession` -> `InteractiveRaptorEngine.refine_node()` -> `SummarizationAgent` (with Refinement Strategy) -> `DiskChunkStore` (Update) -> `InteractiveSession` (Notify Update) -> GUI Refresh.

```mermaid
graph TD
    subgraph "Interface Layer"
        CLI[Command Line Interface]
        GUI[Matome Canvas (Panel)]
    end

    subgraph "MVVM State Management"
        VM[Interactive Session (ViewModel)]
    end

    subgraph "Application Layer"
        IRE[Interactive Raptor Engine]
        RE[Core Raptor Engine]
        SA[Summarization Agent]
        VA[Verifier Agent]
        STRAT[Prompt Strategies]
    end

    subgraph "Domain & Data Layer"
        Store[DiskChunkStore (SQLite)]
        Models[Pydantic Models]
        Embed[Embedding Service]
    end

    CLI --> RE
    GUI <--> VM
    VM <--> IRE
    IRE --> Store
    IRE --> SA
    RE --> SA
    RE --> VA
    RE --> Cluster[Clustering Service]
    RE --> Store

    SA -.-> STRAT
    SA --> Models
    Store --> Models

    style GUI fill:#f9f,stroke:#333,stroke-width:2px
    style VM fill:#aff,stroke:#333,stroke-width:2px
    style IRE fill:#ffa,stroke:#333,stroke-width:2px
```

## 4. Design Architecture

The detailed design architecture focuses on the file structure, class responsibilities, and data modeling that underpin the system. The project follows a "Domain-Driven Design" (DDD) inspired approach, where domain models are central and agnostic to the infrastructure.

### File Structure (Ascii Tree)

```text
src/
├── domain_models/          # Core Pydantic Models (Shared Kernel)
│   ├── chunk.py            # Chunk, SummaryNode definitions
│   ├── config.py           # Configuration classes
│   └── metadata.py         # NodeMetadata, DIKW enums
├── matome/
│   ├── agents/             # AI Logic
│   │   ├── strategies.py   # NEW: PromptStrategy implementations (Wisdom, etc.)
│   │   ├── summarizer.py   # Updated SummarizationAgent
│   │   └── verifier.py     # VerifierAgent
│   ├── engines/            # Core Processing Engines
│   │   ├── raptor.py       # Batch Raptor Engine
│   │   ├── interactive.py  # NEW: InteractiveRaptorEngine
│   │   ├── chunker.py      # Japanese Semantic Chunker
│   │   └── cluster.py      # GMM Clustering
│   ├── ui/                 # NEW: GUI Components
│   │   ├── app.py          # Panel App Entry Point
│   │   ├── view_model.py   # InteractiveSession
│   │   └── components/     # UI Widgets (Pyramid, Chat)
│   └── utils/
│       └── store.py        # DiskChunkStore (SQLite Wrapper)
```

### Key Class Definitions

1.  **`NodeMetadata` (in `metadata.py`)**:
    *   **Role**: Extends the existing metadata to support DIKW.
    *   **Fields**:
        *   `dikw_level`: `Enum("wisdom", "knowledge", "information", "data")`
        *   `refinement_history`: `List[RefinementRecord]` - audit trail of changes.
        *   `is_user_locked`: `bool` - prevents auto-overwrite.
    *   **Invariants**: A node cannot have a `dikw_level` of `data` if it is a summary node.

2.  **`PromptStrategy` (Protocol in `strategies.py`)**:
    *   **Role**: Defines how to prompt the LLM and parse the result.
    *   **Methods**:
        *   `generate_prompt(context: str, instruction: str) -> str`
        *   `parse_output(response: str) -> str`
    *   **Implementations**:
        *   `WisdomStrategy`: Enforces brevity, abstractness, and "aphorism" style.
        *   `KnowledgeStrategy`: Enforces structural explanation ("Why", "Mechanism").
        *   `ActionStrategy`: Enforces checklist/bullet-point format.

3.  **`InteractiveRaptorEngine` (in `interactive.py`)**:
    *   **Role**: Controller for the GUI.
    *   **Methods**:
        *   `refine_node(node_id: str, instruction: str) -> SummaryNode`: Fetches node, applies strategy, calls LLM, saves result.
        *   `get_tree_view(root_id: str, depth: int) -> Dict`: Returns a JSON-serializable tree structure for the UI.

4.  **`InteractiveSession` (in `view_model.py`)**:
    *   **Role**: ViewModel for the Panel app.
    *   **Attributes (Reactive)**:
        *   `current_node`: `SummaryNode`
        *   `chat_history`: `List[Message]`
        *   `is_processing`: `bool`
    *   **Behaviors**: Updates attributes based on user actions; triggers `InteractiveRaptorEngine` methods.

### Data Models & Schema

The system relies heavily on Pydantic for schema validation. This ensures that even in a dynamic Python environment, data integrity is preserved. For the DIKW transition, we utilize the `extra="allow"` capability of Pydantic models (or explicit field addition) to add `dikw_level` without breaking existing databases, although a migration script (or "lazy migration" logic in code) will be preferred to ensure consistency.

## 5. Implementation Plan

The development is divided into 5 sequential cycles. Each cycle builds upon the previous one, moving from core backend refactoring to the final polished user experience.

### **Cycle 01: Core Architecture Refactoring**
**Goal**: Prepare the codebase for DIKW by implementing the Strategy Pattern and updating data models.
*   **Tasks**:
    1.  Define `PromptStrategy` Protocol.
    2.  Refactor `SummarizationAgent` to accept a strategy instance.
    3.  Update `NodeMetadata` to include `dikw_level`, `refinement_history`.
    4.  Create `BaseSummaryStrategy` (preserves current behavior) as the default.
*   **Deliverable**: A refactored backend that works exactly like the old one (CLI passes all regression tests) but is ready for new strategies.

### **Cycle 02: DIKW Generation Engine**
**Goal**: Implement the "Semantic Zooming" logic (The "Brain").
*   **Tasks**:
    1.  Implement `WisdomStrategy`: Prompts for high-level abstraction.
    2.  Implement `KnowledgeStrategy`: Prompts for logical structures.
    3.  Implement `ActionStrategy`: Prompts for actionable checklists.
    4.  Update `RaptorEngine` (or create a subclass/mode) to apply these strategies at appropriate tree levels (Level 0 -> Action, Level 1 -> Knowledge, Root -> Wisdom).
*   **Deliverable**: A CLI mode (`--mode dikw`) that generates a `summary_dikw.md` with clear hierarchical distinction.

### **Cycle 03: Interactive Backend**
**Goal**: Build the API layer for the GUI and handle concurrency.
*   **Tasks**:
    1.  Create `InteractiveRaptorEngine`.
    2.  Implement `Single Node Refinement` logic (load -> prompt -> update -> save).
    3.  Harden `DiskChunkStore` with context managers (`with sqlite3.connect...`) to ensure thread safety during concurrent read/write.
*   **Deliverable**: A Python API that allows querying and updating individual nodes programmatically.

### **Cycle 04: GUI Foundation (MVVM)**
**Goal**: Create the visual shell.
*   **Tasks**:
    1.  Initialize `Panel` application structure.
    2.  Implement `InteractiveSession` (ViewModel) to hold state.
    3.  Create the basic layout: Sidebar (Tree Nav), Main Area (Content), Bottom (Chat).
    4.  Bind `DiskChunkStore` to the ViewModel.
*   **Deliverable**: A launchable web app (`matome ui`) that displays the generated tree (read-only).

### **Cycle 05: Semantic Zooming Experience**
**Goal**: Connect the dots and enable the "Magic".
*   **Tasks**:
    1.  Implement the Pyramid Navigation logic (clicking Wisdom reveals Knowledge).
    2.  Connect the Chat Input to `InteractiveRaptorEngine.refine_node`.
    3.  Implement "Source Verification" (displaying linked raw chunks).
    4.  Final UI polish and CSS styling.
*   **Deliverable**: The complete Matome 2.0 system.

## 6. Test Strategy

Testing is critical to ensure that the complex interactions between the new GUI, the interactive engine, and the existing batch processing pipeline do not introduce regressions or stability issues.

### **Cycle 01 Test Strategy**
*   **Unit Tests**: Verify that `SummarizationAgent` correctly delegates to the injected `PromptStrategy`. Test `NodeMetadata` validation ensures valid DIKW values.
*   **Regression Tests**: Run the full CLI pipeline with `BaseSummaryStrategy` and ensure the output matches the previous version's baseline (byte-for-byte or semantic equivalence).

### **Cycle 02 Test Strategy**
*   **Unit Tests**: Test each new Strategy (`Wisdom`, `Knowledge`, `Action`) in isolation. Feed them a fixed text and assert the output format (e.g., Action strategy produces markdown checkboxes).
*   **Integration Tests**: Run the DIKW pipeline on a sample text. Verify that the root node has `metadata.dikw_level == "wisdom"` and leaf summaries have `metadata.dikw_level == "information"`.

### **Cycle 03 Test Strategy**
*   **Concurrency Tests**: Simulate a "writer" thread updating a node while a "reader" thread queries the tree. Ensure no `sqlite3.OperationalError` (database locked) occurs.
*   **Functional Tests**: Call `refine_node()` with a specific instruction (e.g., "Translate to Japanese") and verify the node's text is updated in the DB and the `refinement_history` is appended.

### **Cycle 04 Test Strategy**
*   **Component Tests**: Instantiate the `InteractiveSession` ViewModel. Simulate user actions (select node) and assert state changes (`current_node` updates).
*   **UI Tests**: Use `playwright` (if applicable) or manual verification to ensure the Panel app launches and renders the initial tree structure without errors.

### **Cycle 05 Test Strategy**
*   **End-to-End (E2E) Tests**: Walk through the "User Test Scenarios".
    *   **Scenario A**: Load a file, check for Wisdom/Knowledge separation.
    *   **Scenario B**: Click a node, refine it via chat, verify the update persists.
    *   **Scenario C**: Check source links.
*   **Usability Testing**: Verify that the "Semantic Zooming" feels intuitive—latency checks for node expansion and chat response.
