# Cycle 03: Interactive Engine & Concurrency - Specification

## 1. Summary

Cycle 03 focuses on transforming the system from a batch processor into an interactive engine capable of supporting real-time user requests. The core deliverable is the `InteractiveRaptorEngine`, a controller class that exposes granular operations like "Get Node," "Get Children," and critically, "Refine Node." To support these operations safely in a GUI environment where background processing might occur, we must implement robust concurrency controls (locking/transactions) within the `DiskChunkStore` to prevent SQLite "database is locked" errors.

## 2. System Architecture

We introduce a new engine module and enhance the storage layer.

```ascii
src/
├── matome/
│   ├── engines/
│   │   ├── **interactive.py**   # NEW: InteractiveRaptorEngine
│   │   └── raptor.py            # MODIFY: Refactor shared logic if needed
│   └── store/
│       └── **chunk_store.py**   # MODIFY: Add Context Manager / Locking
```

**Key Changes:**
1.  **`src/matome/engines/interactive.py`**:
    -   `InteractiveRaptorEngine`: A high-level API for the GUI.
    -   Methods: `get_tree_structure()`, `get_node(id)`, `refine_node(id, instruction)`.
2.  **`src/matome/store/chunk_store.py`** (or where `DiskChunkStore` resides):
    -   Implement `__enter__` / `__exit__` or a `session()` method for transactional scope.
    -   Ensure thread safety using `threading.Lock` or SQLite's native `WAL` mode configuration.

## 3. Design Architecture

### 3.1. InteractiveRaptorEngine

This class acts as the "Controller" in the MVC/MVVM pattern.

```python
class InteractiveRaptorEngine:
    def __init__(self, store: DiskChunkStore, agent: SummarizationAgent):
        self.store = store
        self.agent = agent

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Regenerates a specific node based on user instruction.
        1. Fetch original node & children/context.
        2. Create RefinementStrategy(instruction).
        3. Call agent.summarize(context, strategy).
        4. Update node in DB.
        5. Return updated node.
        """
        ...
```

### 3.2. Concurrency Control (DiskChunkStore)

SQLite allows multiple readers but only one writer. To prevent crashes:

1.  **WAL Mode:** Enable Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) on connection. This significantly improves concurrency.
2.  **Context Manager:**
    ```python
    with store.session() as session:
        node = session.get_node(id)
        node.text = new_text
        session.update(node)
    # Commit happens automatically on exit
    ```
3.  **Retry Logic:** Use `tenacity` library to retry DB operations if a `OperationalError: database is locked` occurs.

## 4. Implementation Approach

### Step 1: Enhance DiskChunkStore
1.  Modify `DiskChunkStore` to accept a `multithread=True` flag (if applicable to the connection).
2.  Execute `PRAGMA journal_mode=WAL;` upon connection.
3.  Implement a `transaction()` or `session()` context manager that handles commits/rollbacks.

### Step 2: Implement RefinementStrategy
1.  In `src/matome/agents/strategies.py`, create `RefinementStrategy`.
2.  Prompt Template:
    "You are an editor. Here is the original text: {text}.
    The user wants to change it: {instruction}.
    Rewrite the text to satisfy the instruction while keeping the core facts."

### Step 3: Create InteractiveRaptorEngine
1.  Create `src/matome/engines/interactive.py`.
2.  Implement `refine_node`:
    -   Retrieve the node.
    -   Construct the "Context" (usually the text of its children).
    -   Invoke `agent.summarize` with `RefinementStrategy`.
    -   Update the node's `text`, `metadata.is_user_edited=True`, and append to `metadata.refinement_history`.
    -   Save to Store.

## 5. Test Strategy

### 5.1. Unit Testing (Refinement)
-   **Mock Agent:** Test `InteractiveRaptorEngine.refine_node` with a mock agent. Verify that the `instruction` is passed correctly to the strategy.
-   **State Update:** Verify that the returned node has `is_user_edited=True` and the history is updated.

### 5.2. Concurrency Testing (Stress Test)
-   **Script:** Create a script that spawns 5 threads.
-   **Action:** Each thread tries to read and write to the *same* `chunks.db` continuously for 10 seconds.
-   **Success:** No exceptions raised. Data is consistent (last write wins).

### 5.3. Integration Testing
-   **Refinement Flow:**
    1.  Create a dummy tree.
    2.  Call `refine_node(root_id, "Make it shorter")`.
    3.  Check DB: The root node text is shorter (if using real LLM) or changed (mock). The ID remains the same. The children links remain valid.
