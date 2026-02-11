# Cycle 03: Interactive Backend - Specification

## 1. Summary

The objective of Cycle 03 is to transform the system from a "Batch Processor" to an "On-Demand Service." The CLI currently processes a file once and exits. The GUI, however, requires the ability to query the existing knowledge graph (stored in `chunks.db`) and update specific nodes based on user feedback without reprocessing the entire tree.

We will introduce the `InteractiveRaptorEngine` (or `RaptorController`), a class designed to be long-lived and stateful. It will wrap the `DiskChunkStore` and `SummarizationAgent` to provide an API for:
1.  **Random Access**: Retrieve a specific node by ID along with its children/parents.
2.  **Single Node Refinement**: Take a node ID and a user instruction ("Make this simpler"), re-generate the summary using a new `RefinementStrategy`, and update the database.
3.  **Concurrency Safety**: Since the GUI (Panel) may run in a separate thread or process from the heavy lifting, we must ensure `chunks.db` (SQLite) is accessed safely.

## 2. System Architecture

```text
src/
├── matome/
│   ├── engines/
│   │   ├── **interactive.py**      # CREATED: InteractiveRaptorEngine
│   │   └── raptor.py             # (No major change, maybe some helper extraction)
│   ├── agents/
│   │   └── **strategies.py**       # UPDATED: Add RefinementStrategy
│   └── utils/
│       └── **store.py**            # UPDATED: Add thread-safe context managers
tests/
├── **test_interactive.py**         # CREATED: Test refinement logic
└── **test_concurrency.py**         # CREATED: Test DB locking behavior
```

### Key Components

*   **`InteractiveRaptorEngine`**: The main entry point for the GUI.
*   **`RefinementStrategy`**: A new strategy that takes `(original_text, instruction)` as input and produces `refined_text`.
*   **`DiskChunkStore`**: Enhanced with `threading.Lock()` or better SQLite pragma handling (WAL mode) for concurrent access.

## 3. Design Architecture

### 3.1. InteractiveRaptorEngine

```python
class InteractiveRaptorEngine:
    def __init__(self, store: DiskChunkStore, agent: SummarizationAgent):
        self.store = store
        self.agent = agent

    def get_node(self, node_id: str) -> SummaryNode:
        """Retrieves a node by ID."""
        return self.store.get_node(node_id)

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Refines a node's summary based on user instruction.
        1. Fetch node.
        2. Construct prompt using RefinementStrategy(original_text, instruction).
        3. Call LLM.
        4. Update node.text and metadata.refinement_history.
        5. Save to store.
        """
        node = self.store.get_node(node_id)
        # ... implementation details ...
        return updated_node
```

### 3.2. RefinementStrategy

```python
class RefinementStrategy:
    def __init__(self, instruction: str):
        self.instruction = instruction

    def generate_prompt(self, text: str, context: str = "") -> str:
        return f"""
Original Text:
{text}

User Instruction:
{self.instruction}

Please rewrite the text following the instruction.
"""
```

### 3.3. Concurrency (DiskChunkStore)

SQLite is file-based. To support a responsive UI that might query while an update is happening:
1.  **WAL Mode**: Enable Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) to allow simultaneous readers and writers.
2.  **Context Manager**:
    ```python
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    ```

## 4. Implementation Approach

### Step 1: Enhance DiskChunkStore
1.  Modify `src/matome/utils/store.py`.
2.  Ensure every DB operation opens/closes a connection or uses a thread-local connection.
3.  Enable WAL mode in `__init__`.

### Step 2: Implement RefinementStrategy
1.  Add `RefinementStrategy` to `src/matome/agents/strategies.py`.

### Step 3: Create InteractiveRaptorEngine
1.  Create `src/matome/engines/interactive.py`.
2.  Implement `refine_node` logic:
    *   Load node.
    *   Create strategy with user instruction.
    *   `agent.summarize(node.text, strategy=refinement_strategy)`.
    *   Update `node.text`.
    *   Append to `node.metadata.refinement_history`.
    *   `store.save_node(node)`.

## 5. Test Strategy

### 5.1. Unit Tests

**`tests/test_interactive.py`**
*   **Test Refinement**:
    *   Mock the agent to return "Refined Text".
    *   Call `engine.refine_node("id_1", "Make it shorter")`.
    *   Assert `node.text == "Refined Text"`.
    *   Assert `len(node.metadata.refinement_history) == 1`.

### 5.2. Concurrency Tests

**`tests/test_concurrency.py`**
*   **Simulate Race Conditions**:
    *   Create a `store` instance.
    *   Spawn a thread that writes to a node repeatedly.
    *   Spawn a thread that reads the same node repeatedly.
    *   Run for 2 seconds.
    *   Assert no exceptions (Database Locked) occurred.
