# System Architecture: Matome 2.0 "Knowledge Installation"

## 1. Summary

The Matome 2.0 project represents a significant evolutionary leap from a static command-line summarization tool to a dynamic, interactive "Knowledge Installation" system. The core philosophy driving this transformation is the concept of "Semantic Zooming"—a user interface paradigm that allows users to traverse information at varying levels of abstraction, from high-level philosophical insights (Wisdom) down to raw evidentiary data (Data).

In the current information-rich environment, users are often overwhelmed by the sheer volume of text. Traditional summarization tools offer a static reduction of content, often losing context or failing to align with the user's specific mental model. Matome 2.0 addresses this by implementing a Reverse-DIKW (Data, Information, Knowledge, Wisdom) hierarchy. Instead of merely shortening text, the system reconstructs the content into a structured pyramid where the "Wisdom" (the core message or lesson) sits at the apex, supported by "Knowledge" (frameworks and logic), "Information" (actionable steps), and grounded in "Data" (original text chunks).

This system is built upon the robust RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) engine but extends it with an interactive layer. Users are not passive consumers of a summary; they are active participants in the knowledge construction process. Through a "Matome Canvas" GUI, users can visualize the knowledge structure, drill down into details, and, crucially, refine the content. If a specific summary node feels too abstract or misses the point, the user can instruct the system to "rewrite this for a 5-year-old" or "focus on the financial implications," triggering a targeted regeneration of that node and its subtree.

The architecture is designed for modularity and scalability. It decouples the summarization logic (via the Prompt Strategy Pattern) from the execution engine, allowing for flexible adaptation to different domains or user needs. The separation of the "Batch Processing Engine" (for initial tree generation) and the "Interactive Engine" (for real-time refinement) ensures that the system can handle large-scale document processing while remaining responsive to user input. By leveraging modern Python technologies like `Panel` for the GUI, `Pydantic` for strict data validation, and `SQLite` for efficient local storage, Matome 2.0 aims to provide a professional, enterprise-grade tool for knowledge workers, researchers, and lifelong learners.

## 2. System Design Objectives

The design of Matome 2.0 is guided by several critical objectives that balance technical robustness with superior user experience.

**1. Semantic Zooming & DIKW Alignment:**
The primary objective is to enable "Semantic Zooming." The system must strictly organize content into the DIKW hierarchy. The "Wisdom" layer must capture the essence of the document in a profound, memorable way (20-40 characters). "Knowledge" must provide the structural "why," "Information" must offer actionable "how," and "Data" must provide the evidentiary "what." This hierarchy must be navigable in real-time, allowing users to zoom in and out of details instantly.

**2. Interactivity & User Agency:**
Unlike the previous version, the system must support "Human-in-the-Loop" refinement. The architecture must support granular updates—regenerating a specific node without rebuilding the entire tree. This requires a sophisticated state management system where the user's intent (e.g., "simplify this") is captured and translated into specific prompt strategies that modify the content while maintaining consistency with the surrounding nodes.

**3. Modularity & Extensibility:**
The system must be built to last and evolve. Hard-coding prompts or logic into the core engine is strictly prohibited. We will adopt the "Prompt Strategy Pattern," where summarization logic is encapsulated in swappable strategy classes. This allows developers (and potentially users in the future) to create custom strategies (e.g., "Academic Paper Mode," "Tweet Thread Mode") without touching the core engine code.

**4. Data Integrity & Traceability:**
In the era of AI hallucinations, trust is paramount. The system must maintain strict traceability. Every piece of high-level Wisdom must be traceable back to the specific Data chunks that generated it. The architecture must enforce this linkage through the `children_indices` property of `SummaryNodes`, ensuring that a user can always verify the source of an AI-generated claim. Furthermore, all data structures must be strictly validated using `Pydantic` to prevent schema drift and ensure type safety.

**5. Performance & Concurrency:**
Transitioning to a GUI implies that the backend might be accessed concurrently (e.g., the UI reading data while the engine is writing updates). The `DiskChunkStore` (SQLite wrapper) must be robust against such concurrency. We will implement Write-Ahead Logging (WAL) and proper transaction management (Context Managers) to ensure that the user interface never freezes and data is never corrupted, even during intensive refinement operations.

## 3. System Architecture

The system follows a layered architecture, separating the Presentation Layer (UI), Application Layer (Engines), Domain Layer (Strategies & Models), and Infrastructure Layer (Storage).

### High-Level Architecture Diagram

```mermaid
graph TD
    User[User] -->|Interacts| GUI[Matome Canvas (Panel)]

    subgraph Presentation Layer
        GUI -->|View State| VM[InteractiveSession (ViewModel)]
        GUI -->|Refine Request| Controller[InteractiveRaptorEngine]
    end

    subgraph Application Layer
        Controller -->|Get Nodes| Store[DiskChunkStore]
        Controller -->|Summarize/Refine| Agent[SummarizationAgent]
        BatchEngine[RaptorEngine] -->|Initial Build| Store
    end

    subgraph Domain Layer
        Agent -->|Uses| Strategy[PromptStrategy Interface]
        Strategy <|-- WisdomStrat[WisdomStrategy]
        Strategy <|-- KnowledgeStrat[KnowledgeStrategy]
        Strategy <|-- InfoStrat[InformationStrategy]

        DataModel[SummaryNode / Chunk]
    end

    subgraph Infrastructure Layer
        Store -->|Read/Write| DB[(SQLite / chunks.db)]
        Agent -->|API Call| LLM[OpenAI API]
    end

    VM -.->|Observes| Store
```

### Component Descriptions

1.  **Matome Canvas (GUI):**
    Built with `Panel`, this is the user-facing interface. It implements the "Pyramid Navigation" view, displaying the Wisdom node at the top. Clicking a node expands its children (Knowledge/Information). It also hosts the chat interface for sending refinement instructions. It observes the `InteractiveSession` for state changes.

2.  **InteractiveSession (ViewModel):**
    Acts as the glue between the UI and the data. It holds the current navigation state (e.g., `current_root_id`, `selected_node_id`, `breadcrumbs`). It uses `param` to define reactive properties that the GUI listens to. It abstracts the complexity of data retrieval, providing simple methods like `get_current_view()` to the UI.

3.  **InteractiveRaptorEngine (Controller):**
    The core logic provider for the GUI. Unlike the batch `RaptorEngine`, this engine is designed for transactional operations. It handles `refine_node(node_id, instruction)`, which fetches the node's children, selects the appropriate `RefinementStrategy`, calls the `SummarizationAgent`, and updates the `DiskChunkStore`.

4.  **SummarizationAgent & PromptStrategies:**
    The `SummarizationAgent` is the AI worker. Crucially, it is stateless regarding the "type" of summary. It relies on injected `PromptStrategy` objects to determine *how* to summarize.
    -   `WisdomStrategy`: Prompts for abstract, philosophical one-liners.
    -   `KnowledgeStrategy`: Prompts for structural explanations and frameworks.
    -   `InformationStrategy`: Prompts for actionable checklists and how-to guides.

5.  **DiskChunkStore (Infrastructure):**
    A wrapper around SQLite. It handles the persistence of `Chunk` and `SummaryNode` objects. It is enhanced to support concurrency (WAL mode) and provides efficient methods for retrieving node lineages (e.g., getting all leaf chunks for a given summary node).

## 4. Design Architecture

The design architecture focuses on the file structure and the data models that underpin the system. We strictly adhere to `Pydantic` for data modeling to ensure robustness.

### File Structure (ASCII Tree)

```
matome/
├── src/
│   ├── domain_models/          # Core Data Definitions
│   │   ├── __init__.py
│   │   ├── manifest.py         # SummaryNode, Chunk, DocumentTree
│   │   ├── types.py            # Type aliases (NodeID, Metadata)
│   │   └── constants.py        # System constants (DIKW Levels)
│   └── matome/
│       ├── agents/             # AI Logic
│       │   ├── __init__.py
│       │   ├── summarizer.py   # SummarizationAgent
│       │   └── strategies.py   # PromptStrategy implementations (Wisdom, etc.)
│       ├── engines/            # Process Orchestration
│       │   ├── __init__.py
│       │   ├── raptor.py       # Batch RaptorEngine
│       │   └── interactive.py  # InteractiveRaptorEngine (New)
│       ├── ui/                 # User Interface
│       │   ├── __init__.py
│       │   ├── canvas.py       # MatomeCanvas (Panel UI)
│       │   └── view_model.py   # InteractiveSession
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── store.py        # DiskChunkStore (SQLite)
│       │   └── prompts.py      # Raw prompt templates
│       ├── cli.py              # Command Line Interface
│       ├── config.py           # Configuration Management
│       └── __init__.py
├── tests/                      # Comprehensive Test Suite
├── pyproject.toml              # Dependency & Linter Config
├── README.md                   # Project Documentation
└── dev_documents/              # Architecture & Specs
```

### Core Data Models

**1. SummaryNode (Refined):**
We utilize the existing `SummaryNode` but standardize the `metadata` field to enforce the DIKW structure without schema migration.

```python
class NodeMetadata(BaseModel):
    dikw_level: Literal["wisdom", "knowledge", "information", "data"]
    is_user_edited: bool = False
    refinement_history: list[str] = Field(default_factory=list)

class SummaryNode(BaseModel):
    id: str
    text: str
    children_indices: list[int | str]
    metadata: NodeMetadata  # Enforced via Pydantic validation
```

**2. PromptStrategy Interface:**
An abstract base class that defines the contract for all summarization logic.

```python
class PromptStrategy(ABC):
    @abstractmethod
    def format_prompt(self, context: str, children_text: list[str]) -> str:
        pass

    @property
    @abstractmethod
    def target_dikw_level(self) -> str:
        pass
```

### Key Invariants & Constraints
-   **Immutable IDs:** Node IDs must never change once created, even if the content is refined. This ensures that the tree structure remains valid.
-   **Strict Hierarchy:** A generic `SummaryNode` cannot have a `Chunk` as a parent. The flow is always Data -> Information -> Knowledge -> Wisdom (bottom-up generation) or Wisdom -> Data (top-down navigation).
-   **Stateless Agents:** The `SummarizationAgent` must not hold state between calls. All context must be passed via arguments or the injected Strategy.

## 5. Implementation Plan

The project is divided into 5 distinct execution cycles. Each cycle delivers a complete, testable increment of functionality.

**CYCLE 01: Core Architecture & DIKW Strategy Engine**
-   **Focus:** Backend Logic, Prompt Engineering.
-   **Features:**
    -   Refactor `SummarizationAgent` to use `PromptStrategy`.
    -   Implement `WisdomStrategy`, `KnowledgeStrategy`, `InformationStrategy`.
    -   Update `RaptorEngine` to assign DIKW levels during tree generation.
    -   Basic CLI support to generate a "DIKW Tree".
-   **Outcome:** A CLI tool that generates a summary tree where nodes are correctly tagged with DIKW levels and the content reflects the requested abstraction (e.g., Wisdom is short and philosophical).

**CYCLE 02: Interactive Engine & Backend Persistence**
-   **Focus:** Data Management, Refinement Logic.
-   **Features:**
    -   Implement `InteractiveRaptorEngine` class.
    -   Implement `refine_node` method: Fetch children -> Apply `RefinementStrategy` -> Update DB.
    -   Enhance `DiskChunkStore` with Context Managers for thread-safe SQLite access.
    -   Implement logic to lock nodes (`is_user_edited`) to prevent overwrite by batch processes.
-   **Outcome:** A backend capable of updating a single node's text based on user input without corrupting the database.

**CYCLE 03: Basic GUI - The "Read" Experience**
-   **Focus:** User Interface (Panel), Visualization.
-   **Features:**
    -   Set up the `Panel` application structure.
    -   Implement `InteractiveSession` (ViewModel) to manage navigation state.
    -   Implement `MatomeCanvas` (View) with "Pyramid Navigation".
    -   Render the tree starting from L1 (Wisdom) and allow drill-down to L3 (Information).
-   **Outcome:** A web-based viewer where users can explore the generated DIKW tree.

**CYCLE 04: Interactive Refinement - The "Write" Experience**
-   **Focus:** Interaction, Integration.
-   **Features:**
    -   Add "Edit/Refine" controls to the `MatomeCanvas`.
    -   Connect the GUI to `InteractiveRaptorEngine.refine_node`.
    -   Implement a Chat Interface for natural language refinement instructions.
    -   Real-time UI updates upon successful refinement.
-   **Outcome:** A fully interactive "Knowledge Installation" tool where users can rewrite the summary tree.

**CYCLE 05: Polish, Traceability & Final Release**
-   **Focus:** Trust, UX, Documentation.
-   **Features:**
    -   Implement "Source Verification": Click a node to see original `Chunk` text.
    -   Visual polish (CSS styling, better layout for the pyramid).
    -   Comprehensive UAT and "Gold Master" Tutorial creation.
    -   Finalize `README.md` and documentation.
-   **Outcome:** A production-ready release of Matome 2.0.

## 6. Test Strategy

We will employ a multi-level testing strategy to ensure reliability and correctness.

**1. Unit Testing (Pytest):**
-   **Strategies:** Test each `PromptStrategy` to ensure it formats prompts correctly.
-   **Agents:** Mock LLM responses to verify that `SummarizationAgent` handles outputs and errors correctly.
-   **Store:** Test `DiskChunkStore` with concurrent read/write threads to verify locking mechanisms (using `sqlite3` in WAL mode).
-   **Models:** Verify `Pydantic` validation rules (e.g., ensuring `start_char_idx` < `end_char_idx`).

**2. Integration Testing:**
-   **Engine-Store:** Verify that `InteractiveRaptorEngine` correctly retrieves nodes from the store, calls the agent, and updates the store.
-   **Full Cycle:** Run a mini-batch process on a small text file to ensure the full pipeline (Chunking -> Summarization -> Tree Building) works with the new DIKW logic.

**3. User Acceptance Testing (UAT):**
-   **Scenario-Based:** We will define specific scenarios (e.g., "The Grok Moment") and verify them manually using the GUI.
-   **Marimo Tutorials:** We will use `marimo` notebooks to create executable tutorials. These serve as both documentation and automated UAT scripts (where possible) to verify that the API surface remains consistent.
-   **Visual Verification:** Since "Wisdom" is subjective, human review is required. We will use the Canvas to visually inspect if the L1 nodes are truly "wise" and L3 nodes are "actionable."

**4. Performance Testing:**
-   **Latency:** Measure the time taken for `refine_node`. It should be within acceptable limits (e.g., < 10 seconds for an LLM call).
-   **Scalability:** Ensure the UI remains responsive even with a tree containing 1000+ nodes (though typical usage is smaller).

**5. Continuous Integration:**
-   Linting with `ruff` and type checking with `mypy` (strict mode) will be enforced on every commit to maintain code quality.
