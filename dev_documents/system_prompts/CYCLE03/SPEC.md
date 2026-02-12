# Cycle 03 Specification: Interactive Backend

## 1. Summary

Cycle 03 establishes the backend infrastructure required to support the interactive GUI features planned for Cycle 04. While `RaptorEngine` handles batch processing, the new **`InteractiveRaptorEngine`** is designed for low-latency, random-access operations. Its primary responsibility is to fetch node details (including children for drill-down) and to process user refinement requests (editing a node's content). This cycle also addresses the critical requirement of **database concurrency**, ensuring that simultaneous read/write operations from the GUI and CLI do not corrupt the `DiskChunkStore`.

## 2. System Architecture

```ascii
src/matome/
├── agents/
│   └── strategies.py           # Modified: Add RefinementStrategy
├── engines/
│   ├── **interactive.py**      # New: InteractiveRaptorEngine
│   └── raptor.py
├── **interfaces.py**           # Modified: Ensure DiskChunkStore is thread-safe
└── ...
```

### Key Changes
1.  **`src/matome/engines/interactive.py`**: Implementation of `InteractiveRaptorEngine`.
2.  **`src/matome/agents/strategies.py`**: Implementation of `RefinementStrategy`.
3.  **`src/matome/interfaces.py`** (or where `DiskChunkStore` resides): Enhancement of the store class to use context managers/locks for SQLite access.

## 3. Design Architecture

### 3.1. Interactive Engine

The `InteractiveRaptorEngine` acts as a controller for the GUI. It does not run the full RAPTOR algorithm. Instead, it operates on a per-node basis.

```python
class InteractiveRaptorEngine:
    def __init__(self, store: DiskChunkStore, agent: SummarizationAgent):
        self.store = store
        self.agent = agent

    def get_node(self, node_id: str) -> SummaryNode:
        """Fetches a single node."""
        ...

    def get_children(self, node_id: str) -> list[SummaryNode]:
        """Fetches the immediate children of a node."""
        ...

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        1. Fetch the node.
        2. Fetch its context (children or original text).
        3. Use SummarizationAgent with RefinementStrategy.
        4. Update the node in DB (content + metadata).
        5. Return the updated node.
        """
        ...
```

### 3.2. Refinement Strategy

This strategy is unique because it takes *two* inputs: the original text and the user instruction.

*   **Prompt Goal:** Rewrite the provided text according to the user's instructions.
*   **Prompt Logic:**
    ```text
    Original Text: {original_text}
    User Instruction: {instruction}
    Task: Rewrite the text to satisfy the instruction. Maintain the core meaning but change the style/format/detail level as requested.
    ```

### 3.3. Concurrency Model

Since `SQLite` supports only one writer at a time, we must ensure that:
*   Read operations use a read-only connection or short-lived transaction.
*   Write operations use a write-ahead log (WAL) mode if possible, or strictly serialized transactions.
*   The `DiskChunkStore` methods should use a `with self.lock:` or `with self.db_connection:` block.

## 4. Implementation Approach

### Step 1: Implement RefinementStrategy
Add `RefinementStrategy` to `src/matome/agents/strategies.py`. It should accept an `instruction` in its `context` dictionary during `format_prompt`.

### Step 2: Implement InteractiveRaptorEngine
Create `src/matome/engines/interactive.py`.
*   Implement `get_node` and `get_children` (read-only).
*   Implement `refine_node` (read-generate-write).
    *   Retrieve the node.
    *   Construct the prompt using the node's current summary and the user's instruction.
    *   Call `agent.summarize(text=node.summary, strategy=RefinementStrategy(instruction=instruction))`.
    *   Update the node object: set `summary` to new text, set `is_user_edited=True`, append instruction to `refinement_history`.
    *   Save to DB.

### Step 3: Harden DiskChunkStore
Review `src/matome/utils.py` (or wherever `DiskChunkStore` is defined).
*   Ensure all DB access is wrapped in context managers.
*   Enable WAL mode for SQLite (`PRAGMA journal_mode=WAL;`) to improve concurrency.

## 5. Test Strategy

### 5.1. Unit Testing
*   **`tests/test_interactive_engine.py`**:
    *   Mock `SummarizationAgent` and `DiskChunkStore`.
    *   Test `refine_node`: Verify that it calls the agent with the correct strategy and updates the store with the new text and metadata.
    *   Test `get_children`: Verify it returns the correct list of nodes.

### 5.2. Integration Testing
*   **`tests/test_concurrency.py`**:
    *   Use `threading` or `multiprocessing` to simulate concurrent access.
    *   Thread A: Reads repeatedly from the DB.
    *   Thread B: Writes updates to the DB via `InteractiveRaptorEngine`.
    *   Assert that no exceptions (e.g., "database is locked") occur and that data is consistent.
*   **`tests/test_refinement_flow.py`**:
    *   Create a node.
    *   Refine it.
    *   Refine it again.
    *   Check `refinement_history` has 2 entries.
    *   Check `is_user_edited` is True.
