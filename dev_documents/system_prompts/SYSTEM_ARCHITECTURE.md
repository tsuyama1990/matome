# System Architecture: Matome 2.0 "Knowledge Installation"

## 1. Summary

The **Matome 2.0** project represents a significant evolution from a static summarization tool to an interactive "Knowledge Installation" system. In the modern era of information overload, users are drowning in data but starving for wisdom. Traditional summarization tools merely compress text, often losing the nuance and structure required for deep understanding. Matome 2.0 addresses this by shifting the paradigm from "Summarization" to "Semantic Zooming" based on the **DIKW (Data, Information, Knowledge, Wisdom)** hierarchy.

The core philosophy of Matome 2.0 is that true understanding comes from the ability to traverse different levels of abstraction. Users should be able to view a document as a single, profound "Wisdom" (L1), expand it into structural "Knowledge" (L2), drill down into actionable "Information" (L3), and finally verify it against the raw "Data" (L4). This process mirrors the cognitive function of the human brain, which constantly switches between high-level pattern recognition and low-level detail processing.

To achieve this, the system introduces a **Semantic Zooming Engine** powered by a reverse-DIKW logic. Instead of just shortening text, the engine restructures it. The root of the document tree becomes the "Wisdom" layer, capturing the philosophical core. The branches become "Knowledge," explaining the "Why" and "How" of the underlying mechanisms. The leaves (or twigs) become "Information," providing concrete action items. This hierarchical structure is not static; it is a living entity that users can interact with.

The **Matome Canvas**, a new interactive GUI built with the Panel library, serves as the cockpit for this experience. It allows users to visualize the knowledge tree as a pyramid or a map. More importantly, it enables **Interactive Refinement**. Users are not passive consumers of AI-generated content. They can challenge the AI, asking it to rewrite specific nodes to better fit their mental models—for example, "Explain this concept using an analogy for a 10-year-old" or "Make this action item more specific to my industry."

Technically, this requires a shift from a batch-processing architecture to an interactive, stateful one. The system must support random access to nodes, granular updates without re-processing the entire tree, and concurrent access to the underlying data store. The architecture leverages the robust **RAPTOR** engine but wraps it in an interactive controller layer, enabling real-time responsiveness while maintaining data integrity.

In summary, Matome 2.0 is not just a tool for reading less; it is a tool for understanding more. It empowers users to "install" knowledge into their brains by aligning the information structure with their cognitive processes, transforming the act of reading into an act of exploration and mastery.

## 2. System Design Objectives

The design of Matome 2.0 is guided by several critical objectives that ensure the system is robust, scalable, and user-centric.

### 1. Semantic Fidelity and Abstraction Alignment
The primary objective is to ensure that the generated content at each level of the DIKW hierarchy strictly adheres to its definition.
- **Wisdom (L1)** must be abstract, philosophical, and concise (20-40 characters). It should capture the "Soul" of the document.
- **Knowledge (L2)** must be structural and explanatory. It should represent the "Skeleton" or mental model, focusing on relationships and mechanisms rather than isolated facts.
- **Information (L3)** must be actionable and concrete. It represents the "Muscle" that performs tasks.
- **Data (L4)** must be the immutable "Ground Truth," traceable and linked.
The system must enforce these semantic boundaries through rigorous Prompt Engineering and Strategy patterns.

### 2. Interactive Responsiveness
Unlike the previous batch-oriented CLI, the new GUI must respond to user actions immediately.
- **Latency**: Node expansion (drilling down) should be near-instantaneous.
- **Refinement**: Node regeneration requests (chat interactions) must be processed asynchronously but provide immediate feedback (loading states).
- **State Management**: The UI must accurately reflect the state of the underlying data, even when multiple operations are happening. This requires a reactive architecture (MVVM) where the View automatically updates in response to Model changes.

### 3. Granular Modularity and Extensibility
The codebase must be modular to support future enhancements and different processing modes.
- **Strategy Pattern**: The summarization logic must be decoupled from the execution engine. We should be able to plug in different "Prompt Strategies" (e.g., Academic, Business, Creative) without changing the core engine code.
- **Engine Wrapper**: The `RaptorEngine` should remain a pure processing engine, while user interaction logic is encapsulated in an `InteractiveRaptorEngine` wrapper. This separation of concerns ensures that the core algorithms remain clean and testable.

### 4. Data Integrity and Concurrency
With the introduction of an interactive GUI, the system moves from a single-threaded batch process to a potentially multi-threaded environment (or at least one where the UI thread and processing threads interact).
- **Database Safety**: The SQLite database (`chunks.db`) must be protected against race conditions. We need to implement robust locking mechanisms or transaction management to ensure that user edits and background processing do not corrupt the data.
- **Traceability**: Every piece of generated content must remain traceable to its source. Updates to a node must preserve these links.

### 5. User-Centric "Aha!" Experience
The ultimate goal is user satisfaction. The system is designed to facilitate "Aha!" moments.
- **Visual Clarity**: The UI should not overwhelm the user. It should present information progressively (Progressive Disclosure).
- **Customizability**: Users should feel like they are building their *own* knowledge base, not just viewing a static report. The ability to edit and refine nodes is crucial for this sense of ownership.

## 3. System Architecture

The architecture of Matome 2.0 is built upon a layered approach, separating the presentation layer (GUI), the application logic (Interactive Engine), the domain logic (Strategies), and the data persistence layer.

```mermaid
graph TD
    User[User] -->|Interacts| Canvas[Matome Canvas (GUI)]

    subgraph "Presentation Layer (MVVM)"
        Canvas -->|Binds| VM[InteractiveSession (ViewModel)]
        VM -->|Updates| Canvas
    end

    subgraph "Application Layer"
        VM -->|Calls| IRE[InteractiveRaptorEngine]
        IRE -->|Manages| SA[SummarizationAgent]
        IRE -->|Manages| ES[EmbeddingService]
    end

    subgraph "Domain Logic (Strategies)"
        SA -->|Uses| PS[<<interface>> PromptStrategy]
        PS <|..| WS[WisdomStrategy]
        PS <|..| KS[KnowledgeStrategy]
        PS <|..| IS[InformationStrategy]
    end

    subgraph "Data Layer"
        IRE -->|Reads/Writes| DCS[DiskChunkStore]
        DCS -->|Persists| DB[(SQLite: chunks.db)]
        DCS -->|Persists| VecDB[(Vector Store)]
    end

    User -->|Refinement Request| Canvas
    Canvas -->|Action| VM
    VM -->|Refine Node| IRE
    IRE -->|Select Strategy| SA
    SA -->|Generate| LLM[LLM Service]
    LLM -->|Result| SA
    SA -->|Update| DCS
    DCS -->|Notify| VM
```

### Components Description

1.  **Matome Canvas (GUI)**:
    - Built using the `Panel` library.
    - Responsible for rendering the DIKW tree and handling user input (clicks, chat messages).
    - It observes the `InteractiveSession` ViewModel and updates the display reactively.

2.  **InteractiveSession (ViewModel)**:
    - Holds the state of the user's session: current view, selected node, navigation history, and edit mode status.
    - Uses the `param` library to define reactive properties.
    - Acts as the bridge between the View and the Engine, translating UI events into business logic calls.

3.  **InteractiveRaptorEngine**:
    - A wrapper around the core processing logic.
    - Provides methods for **Single Node Refinement** (`refine_node`).
    - Manages the lifecycle of `SummarizationAgent` and `DiskChunkStore`.
    - Handles concurrency control (DB locking) to ensure safe updates.

4.  **SummarizationAgent & PromptStrategy**:
    - The `SummarizationAgent` is refactored to accept a `PromptStrategy`.
    - `PromptStrategy` is a protocol defining how to construct prompts for different DIKW levels.
    - `WisdomStrategy`, `KnowledgeStrategy`, and `InformationStrategy` implement this protocol, injecting specific instructions for each level of abstraction.

5.  **DiskChunkStore**:
    - Manages persistence of `SummaryNode` objects and raw text chunks.
    - Uses SQLite for metadata/relationships and a vector store (or array) for embeddings.
    - Enhanced to support transactional updates for single nodes.

## 4. Design Architecture

The project structure is designed to be clean, modular, and strictly typed using Pydantic.

### File Structure
```
.
├── pyproject.toml
├── README.md
├── src
│   ├── domain_models
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration models
│   │   └── schema.py          # SummaryNode, NodeMetadata (Pydantic)
│   └── matome
│       ├── __init__.py
│       ├── cli.py             # CLI Entry point
│       ├── agents
│       │   ├── __init__.py
│       │   ├── summarizer.py  # SummarizationAgent
│       │   ├── verifier.py    # VerifierAgent
│       │   └── strategies.py  # NEW: PromptStrategy implementations
│       ├── engines
│       │   ├── __init__.py
│       │   ├── raptor.py      # Core RAPTOR logic
│       │   ├── interactive.py # NEW: InteractiveRaptorEngine
│       │   ├── chunker.py
│       │   ├── embedder.py
│       │   └── cluster.py
│       ├── ui
│       │   ├── __init__.py
│       │   ├── canvas.py      # NEW: MatomeCanvas (View)
│       │   └── session.py     # NEW: InteractiveSession (ViewModel)
│       ├── utils
│       │   ├── __init__.py
│       │   └── store.py       # DiskChunkStore
│       └── interfaces.py      # Protocols
└── tests
    ├── unit
    ├── integration
    └── uat
```

### Data Models

**NodeMetadata (Updated)**
The `metadata` field in `SummaryNode` is crucial for the DIKW implementation. It will be enhanced to support:

```python
from enum import StrEnum
from pydantic import BaseModel, Field

class DIKWLevel(StrEnum):
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"

class NodeMetadata(BaseModel):
    dikw_level: DIKWLevel
    is_user_edited: bool = False
    refinement_history: list[str] = Field(default_factory=list)
    # Existing fields...
    cluster_id: int | None = None
```

This schema ensures that every node knows its place in the abstraction hierarchy and tracks its modification history, which is essential for the "User-Edited Lock" feature (preventing overwrites during batch updates).

## 5. Implementation Plan

The development is divided into 5 sequential cycles to ensure stability and iterative value delivery.

### Cycle 01: Core Refactoring & Strategy Pattern
**Goal**: Decouple prompt logic from the agent to support DIKW levels.
- **Features**:
    - Define `PromptStrategy` protocol.
    - Implement `WisdomStrategy`, `KnowledgeStrategy`, `InformationStrategy`.
    - Refactor `SummarizationAgent` to accept strategies.
    - Update `NodeMetadata` schema.
- **Tasks**:
    - Create `src/matome/agents/strategies.py`.
    - Modify `src/matome/agents/summarizer.py`.
    - Update `src/domain_models/schema.py`.
    - Write unit tests for each strategy.

### Cycle 02: DIKW Generation Engine
**Goal**: Implement the logic to generate the full DIKW tree automatically.
- **Features**:
    - Update `RaptorEngine` to use different strategies based on tree level.
    - Logic: Root -> Wisdom, Middle -> Knowledge, Leaves -> Information.
    - CLI support for `--mode dikw`.
    - Ensure L4 (Data) linking is preserved.
- **Tasks**:
    - Modify `src/matome/engines/raptor.py` to handle the `dikw` mode.
    - Update `ProcessingConfig` to include mode settings.
    - Integration test: Generate a tree and verify level assignments.

### Cycle 03: Interactive Engine Backend
**Goal**: specific backend support for GUI interactions (random access, updates).
- **Features**:
    - Create `InteractiveRaptorEngine`.
    - Implement `refine_node(node_id, instruction)` method.
    - Implement thread-safe DB access in `DiskChunkStore`.
- **Tasks**:
    - Create `src/matome/engines/interactive.py`.
    - Enhance `src/matome/utils/store.py` with context managers for locking.
    - Test concurrency by simulating simultaneous read/write operations.

### Cycle 04: GUI Foundation (MVVM)
**Goal**: Build the reactive foundation for the user interface.
- **Features**:
    - Implement `InteractiveSession` (ViewModel) using `param`.
    - Create basic `MatomeCanvas` layout using `Panel`.
    - One-way binding: DB -> ViewModel -> View.
- **Tasks**:
    - Create `src/matome/ui/session.py`.
    - Create `src/matome/ui/canvas.py` (skeleton).
    - Create a test script to launch the basic empty canvas.

### Cycle 05: Semantic Zooming & Polish
**Goal**: Complete the GUI with navigation and chat features, and release.
- **Features**:
    - Pyramid Navigation (Click to drill down).
    - Interactive Chat Refinement (User talks to node).
    - Source Traceability (View original chunks).
    - Final Polish (CSS, Loading states).
- **Tasks**:
    - Implement navigation logic in `InteractiveSession`.
    - Connect Chat interface to `refine_node`.
    - styling and UX improvements.
    - End-to-End testing of the full user story.

## 6. Test Strategy

Testing will be rigorous, ensuring both the stability of the core engine and the responsiveness of the new UI.

### Cycle 01: Strategy Unit Tests
- **Objective**: Verify that strategies produce the correct prompts.
- **Method**:
    - Unit tests for `WisdomStrategy`: Check if prompt includes constraints (20-40 chars, abstract).
    - Unit tests for `KnowledgeStrategy`: Check if prompt asks for "Why/How".
    - Mock `SummarizationAgent` to ensure it correctly calls the injected strategy.

### Cycle 02: Hierarchy Integration Tests
- **Objective**: Verify that the engine produces a well-formed DIKW tree.
- **Method**:
    - Run the pipeline on a sample text (`test_data/`).
    - Traverse the resulting tree in the DB.
    - Assert that Root is `wisdom`, Children are `knowledge`, and Leaves are `information`.
    - Assert that `dikw_level` metadata is correctly populated.

### Cycle 03: Backend Concurrency Tests
- **Objective**: Verify that the system handles interactive updates without corruption.
- **Method**:
    - Create a test that initializes `InteractiveRaptorEngine`.
    - Simulate a "Refine" operation while simultaneously trying to read the tree.
    - Verify that DB locks function correctly and no data is lost.
    - Verify `refinement_history` is updated.

### Cycle 04: ViewModel Reactive Tests
- **Objective**: Verify MVVM bindings.
- **Method**:
    - Instantiate `InteractiveSession` without the GUI.
    - Programmatically change the `current_node`.
    - Assert that derived properties (e.g., `child_nodes`, `breadcrumb`) update automatically.
    - This allows testing UI logic without a browser.

### Cycle 05: End-to-End (UAT)
- **Objective**: Verify the full user experience.
- **Method**:
    - **Manual/Scripted UAT**: Follow the `USER_TEST_SCENARIO.md`.
    - Launch the Panel app.
    - Verify the "Aha!" moment (Wisdom display).
    - Perform a Semantic Zoom (Drill down).
    - Perform a Refinement (Chat) and verify the update persists.
    - Check Source Traceability links.
