# System Architecture: Matome 2.0 (Knowledge Installation Update)

## 1. Summary

Matome 2.0 represents a significant evolution from a static document summarization tool to an interactive "Knowledge Installation" platform. The core philosophy shifts from simple "text compression" to "Semantic Zooming" based on the DIKW (Data, Information, Knowledge, Wisdom) hierarchy.

In the previous version, Matome focused on solving the "Lost-in-the-Middle" problem using RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval). Matome 2.0 builds upon this foundation but redefines the tree structure. Instead of generic summaries, the layers now correspond to specific cognitive levels:
*   **Wisdom (L1)**: Profound, abstract truths and aphorisms (The "Why").
*   **Knowledge (L2)**: Structural mental models and frameworks explaining the wisdom.
*   **Information (L3)**: Actionable checklists and concrete steps (The "How").
*   **Data (L4)**: The original source text chunks (The "What").

To support this, the system introduces a Graphical User Interface (GUI) built with **Panel**, allowing users to interactively "zoom" into details or "zoom out" to abstract concepts. Users can also refine specific nodes (e.g., "Make this easier to understand"), transforming the system into a personalized learning companion.

## 2. System Design Objectives

### 2.1. Semantic Zooming (DIKW-Reverse Logic)
The system must generate and maintain a strictly typed hierarchy where the parent-child relationship represents an abstraction gradient. The root must be "Wisdom" (minimal context, high impact), while leaves are "Data".

### 2.2. Interactive Refinement
Unlike the static batch process of v1, v2 allows post-generation editing. Users can request changes to specific nodes without regenerating the entire tree. The system must support **Single Node Refinement** and ensure data consistency.

### 2.3. Separation of Concerns (Strategy Pattern)
To prevent `SummarizationAgent` from becoming a monolithic "God Object" with complex conditional logic (`if level == 0...`), the summarization logic must be decoupled using the **Strategy Pattern**. This allows easy injection of different prompt behaviors (Wisdom vs. Action) and facilitates future extensions.

### 2.4. Maintainability & Type Safety
The system will continue to enforce strict type safety using **Pydantic** and **Python 3.11+** features. The GUI architecture will follow the **MVVM (Model-View-ViewModel)** pattern to keep UI logic separate from business logic, ensuring the codebase remains clean and testable.

### 2.5. Concurrency & Data Integrity
With the introduction of an interactive GUI that may run alongside or after batch processes, the system must safely handle concurrent access to the SQLite database (`chunks.db`).

## 3. System Architecture

The architecture is divided into three main layers: the **Interface Layer** (CLI & GUI), the **Application Layer** (Engines & Agents), and the **Infrastructure Layer** (Storage & Models).

```mermaid
graph TD
    subgraph Interface Layer
        CLI[CLI (Typer)]
        GUI[Matome Canvas (Panel)]
    end

    subgraph Application Layer
        RE[RaptorEngine]
        IRE[InteractiveRaptorEngine]
        SA[SummarizationAgent]
        PS[PromptStrategy Interface]
        VA[VerifierAgent]

        WS[WisdomStrategy]
        KS[KnowledgeStrategy]
        IS[ActionStrategy]

        CLI --> RE
        GUI --> IRE
        RE --> SA
        IRE --> SA

        SA --> PS
        PS <|-- WS
        PS <|-- KS
        PS <|-- IS

        RE --> VA
    end

    subgraph Infrastructure Layer
        DSC[DiskChunkStore (SQLite)]
        EM[EmbeddingService]
        CL[Clusterer (GMM)]

        RE --> DSC
        IRE --> DSC
        RE --> EM
        RE --> CL
    end

    subgraph External
        LLM[LLM API (OpenRouter)]
        SA --> LLM
        VA --> LLM
    end
```

### Key Interactions
1.  **Batch Processing**: The `CLI` invokes `RaptorEngine`. The engine uses `GMMClusterer` to group chunks and `SummarizationAgent` to generate summaries. Depending on the tree level, the engine injects the appropriate `PromptStrategy` (e.g., `ActionStrategy` for L3, `WisdomStrategy` for L1).
2.  **Interactive Mode**: The `Matome Canvas` (GUI) communicates with `InteractiveRaptorEngine`. When a user requests a refinement, `InteractiveRaptorEngine` retrieves the specific node from `DiskChunkStore`, selects a `RefinementStrategy`, and uses `SummarizationAgent` to regenerate the node content.
3.  **Data Flow**: All text chunks and summary nodes are persisted in `DiskChunkStore`. The store manages SQLite connections, ensuring transactions are atomic to prevent race conditions between reading (GUI) and writing (Refinement).

## 4. Design Architecture

### 4.1. File Structure

```ascii
src/matome/
├── agents/
│   ├── strategies.py       # [NEW] PromptStrategy implementations (Wisdom, Knowledge, etc.)
│   ├── summarizer.py       # [MOD] Refactored to use PromptStrategy
│   └── verifier.py
├── engines/
│   ├── interactive_raptor.py # [NEW] Controller for GUI operations
│   ├── raptor.py           # [MOD] Updated to support DIKW logic
│   ├── chunker.py
│   └── cluster.py
├── ui/                     # [NEW] Panel GUI Components
│   ├── canvas.py           # [NEW] View (Layout)
│   └── session.py          # [NEW] ViewModel (InteractiveSession)
├── utils/
│   └── store.py            # [MOD] Added concurrency safety
└── main.py
```

### 4.2. Key Data Models

**Node Metadata (Pydantic)**
We leverage the existing `SummaryNode.metadata` field to store DIKW attributes without altering the DB schema.

```python
class DIKWLevel(StrEnum):
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"

class NodeMetadata(BaseModel):
    dikw_level: DIKWLevel
    is_user_edited: bool = False
    refinement_history: list[str] = Field(default_factory=list)
    # ... existing fields
```

**Prompt Strategy Interface**
```python
class PromptStrategy(Protocol):
    def format_prompt(self, text: str, context: str = "") -> str: ...
    def parse_output(self, output: str) -> str: ...
```

## 5. Implementation Plan

The project is divided into 5 sequential cycles to manage complexity and ensure stability.

*   **CYCLE01: Core Refactoring (Strategy Pattern)**
    *   **Goal**: Decouple prompt logic from `SummarizationAgent`.
    *   **Feature**: Introduce `PromptStrategy` protocol and `BaseSummaryStrategy`. Refactor `SummarizationAgent` to accept a strategy.
    *   **Value**: Prepares the codebase for diverse DIKW logic without breaking existing functionality.

*   **CYCLE02: DIKW Engine Logic**
    *   **Goal**: Implement the "Semantic Zooming" generation logic.
    *   **Feature**: Implement `WisdomStrategy`, `KnowledgeStrategy`, `ActionStrategy`. Update `RaptorEngine` to select strategies based on tree depth.
    *   **Value**: Enables the generation of the DIKW hierarchy (Batch Mode).

*   **CYCLE03: Interactive Backend**
    *   **Goal**: Enable granular access and safe concurrency.
    *   **Feature**: Create `InteractiveRaptorEngine` for single-node operations. Enhance `DiskChunkStore` with context managers for thread-safe DB access.
    *   **Value**: Provides the backend API required by the GUI.

*   **CYCLE04: GUI Foundation (MVVM)**
    *   **Goal**: Establish the user interface structure.
    *   **Feature**: Set up Panel. Create `InteractiveSession` (ViewModel) using `param` to manage state. Create `MatomeCanvas` (View) for basic tree visualization.
    *   **Value**: A runnable (though static) GUI that visualizes the data.

*   **CYCLE05: Semantic Zooming & Polish**
    *   **Goal**: Connect UI to Backend and enable refinement.
    *   **Feature**: Wire GUI events to `InteractiveRaptorEngine`. Implement the "Refinement" chat interface. Final UI polish (CSS, layout).
    *   **Value**: Full "Knowledge Installation" experience (Matome 2.0).

## 6. Test Strategy

### 6.1. Unit Testing
*   **Strategies**: Test each `PromptStrategy` (Wisdom, Knowledge, etc.) in isolation to ensure they format prompts correctly and parse outputs as expected.
*   **Agents**: Mock `PromptStrategy` to test `SummarizationAgent`'s execution flow without calling actual LLMs.
*   **ViewModel**: Test `InteractiveSession` logic (state transitions) without rendering the UI.

### 6.2. Integration Testing
*   **DB Concurrency**: Create tests that simulate concurrent read/write operations on `DiskChunkStore` to verify locking mechanisms.
*   **Pipeline**: Run a mini-RAPTOR process with DIKW strategies to verify the tree structure (parent-child relationships and metadata).

### 6.3. User Acceptance Testing (UAT)
*   **Manual Verification**: Since the "quality" of Wisdom/Knowledge is subjective, UAT will rely heavily on the "User Test Scenario" (Source Verification, Aha! Moment).
*   **Mock Mode**: Use "Mock Mode" (pre-generated LLM responses) to allow deterministic testing of the UI flow during development.
