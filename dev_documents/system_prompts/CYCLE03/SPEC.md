# Cycle 03: Interactive Engine & DB Concurrency - Specification

## 1. Summary

Cycle 03 addresses the backend requirements for the interactive GUI. We must transition from a "batch-only" mindset (CLI) to a "real-time request/response" mindset (GUI). This involves two major components:
1.  **Interactive Engine:** A new `InteractiveRaptorEngine` class that exposes granular methods to manipulate the document tree (e.g., `refine_node`, `get_children`) without re-processing the entire document.
2.  **Database Concurrency:** Since the GUI (reading) and the Engine (writing) might operate simultaneously, we must harden the `DiskChunkStore` (SQLite wrapper) against race conditions and locking errors.

This cycle ensures the system is robust enough to support multiple users (or tabs) and long-running background tasks without crashing.

## 2. System Architecture

### File Structure

```ascii
src/
├── matome/
│   ├── engines/
│   │   ├── **interactive.py**   # [NEW] Engine for GUI interaction
│   │   └── raptor.py            # [MODIFIED] Inherit or use shared components
│   └── utils/
│       └── **store.py**         # [MODIFIED] Add locking/transaction logic
```

## 3. Design Architecture

### 3.1. Interactive Engine (`src/matome/engines/interactive.py`)

This class acts as the API layer for the GUI. It orchestrates the interaction between the `SummarizationAgent` and the `DiskChunkStore`.

```python
class InteractiveRaptorEngine:
    def __init__(self, store: DiskChunkStore, agent: SummarizationAgent):
        self.store = store
        self.agent = agent

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Refines a specific node based on user instruction.
        1. Fetch node & context (children) from store.
        2. Call agent with context + instruction.
        3. Update node text in store.
        4. Mark is_user_edited=True.
        """
        ...

    def get_children(self, node_id: str) -> List[SummaryNode]:
        """Returns child nodes for navigation."""
        ...
```

### 3.2. Database Concurrency (`src/matome/utils/store.py`)

SQLite in Python is generally thread-safe, but multi-threaded writes can cause "database is locked" errors. We will mitigate this using:
-   **WAL Mode (Write-Ahead Logging):** Enables concurrent readers and writers.
-   **Transaction Context Manager:** Ensure atomic commits.
-   **Retries:** Use `tenacity` to retry on `OperationalError`.

```python
from contextlib import contextmanager

class DiskChunkStore:
    # ...
    @contextmanager
    def transaction(self):
        """Yields a session/connection with automatic commit/rollback."""
        try:
            yield
            self.commit()
        except Exception:
            self.rollback()
            raise
```

## 4. Implementation Approach

### Step 1: Harden DiskChunkStore
1.  Add `PRAGMA journal_mode=WAL;` to initialization.
2.  Implement `transaction()` context manager.
3.  Wrap all write operations (insert, update) in `with self.transaction():`.
4.  Decorate critical methods with `@retry(stop=stop_after_attempt(3), wait=wait_fixed(0.1))`.

### Step 2: Implement InteractiveRaptorEngine
1.  Create `src/matome/engines/interactive.py`.
2.  Implement `refine_node`:
    -   Retrieve the target node.
    -   Retrieve its children (context).
    -   Construct a prompt: "Original: {text}\nInstruction: {instruction}".
    -   Call `agent.summarize`.
    -   Update the node in `store`.
3.  Implement `get_children`: Simple query to `store`.

### Step 3: Integration with Agent
1.  Ensure `SummarizationAgent` is stateless enough to handle these ad-hoc requests.

## 5. Test Strategy

### Unit Testing
*   **`tests/unit/test_interactive_engine.py`**:
    *   Mock `DiskChunkStore` and `SummarizationAgent`.
    *   Call `refine_node`.
    *   Assert `agent.summarize` is called with the instruction.
    *   Assert `store.update_node` is called with the new text and `is_user_edited=True`.

### Concurrency Testing (Critical)
*   **`tests/integration/test_db_concurrency.py`**:
    *   Setup: Create a `DiskChunkStore`.
    *   Task A (Writer): Loop 100 times, inserting nodes.
    *   Task B (Reader): Loop 100 times, reading nodes.
    *   Execution: Run Task A and B in parallel using `concurrent.futures.ThreadPoolExecutor`.
    *   Assertion: No "database is locked" exceptions. Final count of nodes matches expected.
