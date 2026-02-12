# System Architecture for Matome 2.0: Knowledge Installation

## 1. Summary

The **Matome 2.0** project represents a significant evolutionary leap from a static text summarization tool to a dynamic, interactive **"Knowledge Installation"** system. The primary objective is to empower users not just to compress information, but to restructure it into a mental model that fits their own cognitive framework. This concept, termed **"Semantic Zooming"**, allows users to traverse information at varying levels of abstraction—from high-level philosophical truths (Wisdom) down to actionable steps (Information) and raw evidence (Data).

The legacy system was a Command Line Interface (CLI) application that processed text files in a batch manner, generating a static summary tree using the RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) algorithm. While effective for compression, it lacked the interactivity required for true understanding. Users could not query the summary, refine the output, or explore the "why" and "how" behind the generated insights.

**Matome 2.0** addresses these limitations by introducing a **Data-Information-Knowledge-Wisdom (DIKW)** hierarchy as the core data structure. Instead of generic summaries, the system now explicitly classifies nodes into four levels:
1.  **Wisdom (L1):** Deep, aphoristic truths that capture the essence of the content. These are short, high-impact statements designed to be memorable and profound.
2.  **Knowledge (L2):** The structural logic and mental models that support the Wisdom. This layer answers "Why is this true?" and provides the framework for understanding.
3.  **Information (L3):** Actionable checklists, rules, and procedures. This layer answers "What should I do?" and provides practical utility.
4.  **Data (L4):** The raw source text chunks that serve as evidence for all upper layers.

To support this new paradigm, the system architecture undergoes a major transformation. A new **Graphical User Interface (GUI)**, built with the **Panel** framework, replaces the CLI as the primary interaction point. This "Matome Canvas" utilizes the **Model-View-ViewModel (MVVM)** pattern to ensure a responsive and maintainable user experience.

Under the hood, the backend is refactored to support **interactive refinement**. The monolithic `SummarizationAgent` is broken down using the **Strategy Pattern**, allowing different prompt strategies to be injected dynamically. This enables the system to switch between "Summarize this chunk" and "Rewrite this node as a metaphor for a 5-year-old" without complex conditional logic. A new **`InteractiveRaptorEngine`** works alongside the existing batch engine to handle single-node updates, ensuring that user edits are reflected immediately in the persistent `DiskChunkStore`.

Ultimately, Matome 2.0 is not just a tool for reading less; it is a tool for understanding more. It transforms passive consumption into active knowledge construction, providing a "Google Earth" experience for text—zooming out to see the big picture and zooming in to verify the details.

## 2. System Design Objectives

The design of Matome 2.0 is guided by several critical objectives, constraints, and success criteria that ensure the final product meets the high standards of a "Knowledge Installation" tool.

### 2.1. Primary Objectives

1.  **Semantic Zooming Capability:** The system must strictly adhere to the DIKW hierarchy. Users must be able to navigate from Wisdom to Data seamlessly. The distinction between levels must be semantically enforced by the AI, ensuring that L1 nodes are truly abstract and L3 nodes are truly actionable.
2.  **Interactive Refinement:** Unlike the "fire-and-forget" nature of the previous version, the new system must support iterative improvement. Users should be able to "chat" with a specific node to refine its content, tone, or format. This requires the backend to support granular, atomic updates to the document tree.
3.  **Robust Concurrency:** With the introduction of a GUI that reads from the database while a potentially long-running CLI process might be writing to it, data integrity is paramount. The system must implement robust transaction management and locking mechanisms to prevent race conditions or database corruption.
4.  **Maintainability and Extensibility:** The use of design patterns like **Strategy** (for prompts) and **MVVM** (for the GUI) is mandated to prevent code spaghetti. The architecture must allow for easy addition of new prompt strategies or UI components without destabilizing the core logic.

### 2.2. Constraints

*   **Language & Runtime:** The system is built on **Python 3.11+**, utilizing modern features like strict type hinting (`mypy` strict mode) and `pydantic` for data validation.
*   **GUI Framework:** The user interface must be implemented using **Panel**. This decision leverages the power of the Python data ecosystem while requiring strict adherence to reactive programming principles (using `param`).
*   **Data Storage:** The system continues to use `SQLite` (via `DiskChunkStore`) for local storage. This imposes constraints on concurrency that must be managed via software logic (e.g., careful connection handling).
*   **No External Services (Logic):** The core summarization logic relies on Large Language Models (LLMs) accessed via APIs (e.g., OpenAI), but the orchestration logic must remain entirely local.

### 2.3. Success Criteria

*   **DIKW Fidelity:** The generated Wisdom nodes must be concise (20-50 chars) and profound. Information nodes must be actionable. The system fails if L1 nodes look like generic summaries.
*   **Responsiveness:** Interactive updates (refining a single node) should feel near-instantaneous (limited only by LLM latency), not requiring a full tree rebuild.
*   **User Experience:** A user should be able to load a complex text (e.g., a book), grasp its core message in seconds (Wisdom), and verify a specific claim by drilling down to the source text (Data) within 3 clicks.
*   **Stability:** The application must not crash during concurrent read/write operations or long-running generation tasks.

## 3. System Architecture

The high-level architecture of Matome 2.0 follows a layered approach, clearly separating the presentation layer (GUI/CLI) from the domain logic and data persistence layers.

### 3.1. Architectural Components

1.  **Presentation Layer:**
    *   **CLI (`matome.cli`):** Retained for batch processing and initial file ingestion. It now supports a `--mode dikw` flag.
    *   **GUI (`matome.canvas`):** The new Panel-based interface. It follows the MVVM pattern, consisting of `MatomeApp` (View) and `InteractiveSession` (ViewModel).

2.  **Application Layer (Controllers):**
    *   **`RaptorEngine`:** The classic engine for batch processing. It builds the initial tree.
    *   **`InteractiveRaptorEngine`:** A new controller designed for the GUI. It handles `refine_node` requests, `get_children` queries, and manages the session state with the `DiskChunkStore`.

3.  **Domain Layer (Core Logic):**
    *   **`SummarizationAgent`:** The brain of the operation. It now accepts a `PromptStrategy` to determine *how* to process text.
    *   **`PromptStrategies`:** A family of classes (`WisdomStrategy`, `KnowledgeStrategy`, `InformationStrategy`) that encapsulate the prompt engineering for each DIKW level.
    *   **`JapaneseSemanticChunker`:** Responsible for splitting raw text into meaningful chunks (L4 Data).

4.  **Data Layer:**
    *   **`DiskChunkStore`:** The abstraction over SQLite. It manages `SummaryNode` objects and their relationships.
    *   **`SummaryNode`:** The core data model, now enhanced with `NodeMetadata` containing DIKW attributes.

### 3.2. Data Flow

1.  **Ingestion:** Raw Text -> `JapaneseSemanticChunker` -> `DiskChunkStore` (L4 Nodes).
2.  **Generation:** `RaptorEngine` reads L4 nodes -> Groups them -> `SummarizationAgent` (using `InformationStrategy`) generates L3 nodes -> Stored in DB. Process repeats for L2 (Knowledge) and L1 (Wisdom).
3.  **Interaction:** User clicks L1 Node in GUI -> `InteractiveSession` requests children from `InteractiveRaptorEngine` -> Engine queries `DiskChunkStore` -> Data returned to GUI.
4.  **Refinement:** User requests edit -> `InteractiveSession` calls `InteractiveRaptorEngine.refine_node(id, instructions)` -> Engine invokes `SummarizationAgent` with `RefinementStrategy` -> New text generated -> DB updated -> GUI notified to refresh.

### 3.3. Mermaid Diagram

```mermaid
graph TD
    User((User))

    subgraph Presentation Layer
        CLI[CLI: matome run]
        GUI[GUI: Matome Canvas]
    end

    subgraph Application Layer
        RE[RaptorEngine (Batch)]
        IRE[InteractiveRaptorEngine (Interactive)]
        Session[InteractiveSession (ViewModel)]
    end

    subgraph Domain Layer
        Agent[SummarizationAgent]
        Strategy[PromptStrategy Interface]
        Wisdom[WisdomStrategy]
        Knowledge[KnowledgeStrategy]
        Info[InformationStrategy]
        Refine[RefinementStrategy]
    end

    subgraph Data Layer
        Store[DiskChunkStore]
        DB[(SQLite: chunks.db)]
    end

    User --> CLI
    User --> GUI

    GUI <--> Session
    Session <--> IRE
    CLI --> RE

    RE --> Agent
    IRE --> Agent

    Agent --> Strategy
    Strategy <.. Wisdom
    Strategy <.. Knowledge
    Strategy <.. Info
    Strategy <.. Refine

    RE --> Store
    IRE --> Store
    Store --> DB
```

## 4. Design Architecture

The design architecture details the code organization and the data models that underpin the system.

### 4.1. File Structure

```ascii
src/matome/
├── agents/
│   ├── __init__.py
│   ├── summarizer.py       # SummarizationAgent
│   └── strategies.py       # Wisdom, Knowledge, Information, Refinement Strategies
├── canvas/
│   ├── __init__.py
│   ├── app.py              # Main Panel App (View)
│   ├── session.py          # InteractiveSession (ViewModel)
│   └── components.py       # Reusable UI Widgets
├── engines/
│   ├── __init__.py
│   ├── raptor.py           # RaptorEngine (Batch)
│   └── interactive.py      # InteractiveRaptorEngine (New)
├── interfaces.py           # Abstract Base Classes / Protocols
├── cli.py                  # CLI Entrypoint
└── utils.py
src/domain_models/
├── __init__.py
└── data_schema.py          # SummaryNode, NodeMetadata (Pydantic)
```

### 4.2. Key Data Models

**`NodeMetadata` (Pydantic Model)**
This schema is updated to handle the DIKW attributes without altering the underlying DB schema.
*   `dikw_level`: Enum (`WISDOM`, `KNOWLEDGE`, `INFORMATION`, `DATA`)
*   `is_user_edited`: Boolean. Locks the node from auto-recalculation.
*   `refinement_history`: List of strings. Logs the prompts used to refine this node.

**`PromptStrategy` (Protocol)**
An interface defining how prompts are constructed.
*   `generate_prompt(text: str, context: dict) -> str`
*   `parse_output(response: str) -> dict`

### 4.3. Class Interaction

*   **`SummarizationAgent`**: Now strictly a runner. It takes a strategy and text, calls the LLM, and returns the result. It does not know *what* it is summarizing (Wisdom vs. Knowledge); it only knows *how* to execute the provided strategy.
*   **`InteractiveSession`**: The bridge between the user and the backend. It holds the state of the UI (e.g., `selected_node_id`, `chat_history`). It observes changes in the model and triggers updates in the View.

## 5. Implementation Plan

The development is divided into 5 sequential cycles, each building upon the last to ensure a stable and verifiable progression.

### CYCLE 01: Core Refactoring & Foundation
**Goal:** Prepare the existing codebase for the Strategy Pattern and DIKW data structures without breaking current functionality.
**Features:**
*   **PromptStrategy Pattern:** Refactor `SummarizationAgent` to accept a `PromptStrategy` object. Implement a `DefaultStrategy` that mimics the current behavior.
*   **Metadata Schema Update:** Update `src/domain_models/data_schema.py` to include `dikw_level`, `is_user_edited`, and `refinement_history` in `NodeMetadata`.
*   **Backward Compatibility:** Ensure that existing databases load correctly with defaults (e.g., `dikw_level="data"`).
*   **Refactor Tests:** Update existing unit tests to inject the `DefaultStrategy`.

### CYCLE 02: DIKW Engine Implementation
**Goal:** Implement the specific logic to generate the Data-Information-Knowledge-Wisdom hierarchy.
**Features:**
*   **Strategy Implementation:** Create `WisdomStrategy`, `KnowledgeStrategy`, and `InformationStrategy` classes in `src/matome/agents/strategies.py`.
*   **Engine Update:** Modify `RaptorEngine` (or subclass it) to use these strategies at the appropriate tree levels. (e.g., Level 3 = Information, Level 2 = Knowledge, Level 1 = Wisdom).
*   **CLI Integration:** Add `--mode dikw` argument to the CLI. When active, the engine uses the DIKW strategies.
*   **Verification:** Verify that the output tree has the correct distinct characteristics for each level.

### CYCLE 03: Interactive Backend
**Goal:** Create the backend machinery required to support granular, random-access updates from a GUI.
**Features:**
*   **InteractiveRaptorEngine:** Create `src/matome/engines/interactive.py`.
*   **Single Node Refinement:** Implement `refine_node(node_id, user_instruction)` method. This fetches the node, its children (context), and uses a `RefinementStrategy` to regenerate it.
*   **RefinementStrategy:** Implement a strategy that takes `(original_text, user_instruction)` and produces `(new_text)`.
*   **DB Concurrency:** Audit and strengthen `DiskChunkStore` with context managers to ensure thread safety during interactive updates.

### CYCLE 04: GUI Foundation (MVVM)
**Goal:** Establish the basic Panel application structure and display the root of the tree.
**Features:**
*   **Project Setup:** Create `src/matome/canvas/` directory structure.
*   **ViewModel:** Implement `InteractiveSession` in `src/matome/canvas/session.py`. It should hold `selected_node` and connect to `InteractiveRaptorEngine`.
*   **View:** Implement `src/matome/canvas/app.py` and `components.py`. Create a basic layout that can launch and display the L1 (Wisdom) node of a generated tree.
*   **Launch Command:** specific command or flag to start the GUI.

### CYCLE 05: Semantic Zooming & Final Polish
**Goal:** Complete the user experience with drill-down navigation, interactive editing, and source verification.
**Features:**
*   **Drill-Down UI:** Implement the navigation logic in the GUI. Clicking a node loads its children (L1 -> L2 -> L3).
*   **Edit Interface:** Add a chat/input box in the UI to send instructions to `refine_node`. Update the UI view upon completion.
*   **Source Linking:** Implement the logic to fetch and display the raw text (L4) when an L3 node is inspected.
*   **Final UAT:** Execute the full "Emin's Shikihou" scenario.
*   **Documentation:** Finalize `README.md` and Tutorials.

## 6. Test Strategy

Testing will be rigorous and layered, moving from unit tests of individual components to full integration tests of the user workflows.

### CYCLE 01 Strategy
*   **Unit Tests:** Verify that `SummarizationAgent` correctly uses the injected strategy. Test `NodeMetadata` validation rules (e.g., ensure `dikw_level` only accepts valid enums).
*   **Regression Tests:** Run the existing test suite to ensure the refactoring hasn't broken the "default" summarization mode.
*   **Data Migration Tests:** Load an old `chunks.db` and verify it automatically adapts to the new schema without errors.

### CYCLE 02 Strategy
*   **Strategy Tests:** Isolate each strategy (`WisdomStrategy`, etc.) and test it against mock LLM responses to ensure it parses output correctly.
*   **Integration Tests:** Run the CLI with `--mode dikw` on a small test file. Inspect the resulting database to verify that nodes at different levels have the correct `dikw_level` metadata.
*   **Prompt Verification:** Manually inspect the generated prompts in logs to ensure they match the "System Prompts" design (e.g., Wisdom prompt enforces character limits).

### CYCLE 03 Strategy
*   **Backend API Tests:** specific tests for `InteractiveRaptorEngine`.
    *   Test `refine_node` updates the specific record in the DB.
    *   Test `get_children` returns the correct linked nodes.
*   **Concurrency Tests:** Simulate a scenario where a read and a write happen simultaneously to `DiskChunkStore`. Verify that locks hold and data is not corrupted.
*   **State Tests:** Verify that `is_user_edited` flag is correctly set to `True` after a refinement.

### CYCLE 04 Strategy
*   **Component Tests:** Test individual UI components (e.g., the Wisdom Card) in isolation to ensure they render parameters correctly.
*   **Session Tests:** Test `InteractiveSession` logic without the UI. Call methods like `select_node()` and check if the internal state variables update correctly.
*   **Smoke Test:** Verify the application launches without errors and connects to the database.

### CYCLE 05 Strategy
*   **E2E UI Tests:** Manual or scripted tests of the full flow.
    *   Load file -> See Wisdom.
    *   Click Wisdom -> See Knowledge.
    *   Click Knowledge -> See Action.
    *   Click Action -> Refine -> Verify text change.
*   **Scenario Verification:** Run the `USER_TEST_SCENARIO.md` ("Emin's Shikihou") and qualitatively judge the output against the Success Criteria (e.g., "Is the Wisdom truly wise?").
*   **Performance Test:** Measure the time taken for a refinement operation. It should be within acceptable limits (e.g., < 10 seconds).
