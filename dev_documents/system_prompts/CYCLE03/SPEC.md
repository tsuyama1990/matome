# Cycle 03 Specification: Interactive Backend & Concurrency

## 1. Summary

Cycle 03 builds the backend infrastructure required for the interactive GUI. Unlike the batch processing in Cycle 0 (CLI), the GUI requires granular, random-access updates to the summary tree. This cycle introduces the `InteractiveRaptorEngine`, which allows users to select a specific node and refine it using natural language instructions. Crucially, this engine must handle database concurrency safely, as the GUI server (Panel) and the background generation tasks may access the SQLite database simultaneously.

## 2. System Architecture

We will implement a new engine class and a refinement strategy.

```ascii
src/
├── matome/
│   ├── engines/
│   │   ├── interactive.py   # [NEW] InteractiveRaptorEngine (Controller)
│   ├── agents/
│   │   └── strategies.py    # [MODIFIED] Add RefinementStrategy
│   └── utils/
│       └── db.py            # [MODIFIED] Ensure Thread-Safe Context Managers
```

**New Classes:**
- **`InteractiveRaptorEngine`**: Handles single-node operations (Read/Update).
- **`RefinementStrategy`**: Handles user-instruction based rewriting.

**Modified Components:**
- **`DiskChunkStore`**: Updated to use context managers (`with sqlite3.connect(...)`) for atomic transactions.
- **`db.py`**: Added `get_db_connection` utility with appropriate `timeout` and `check_same_thread=False` settings.

## 3. Design Architecture

### 3.1. InteractiveRaptorEngine (Controller)

This class acts as the bridge between the UI (Cycle 04) and the data layer. It extends or wraps the existing `RaptorEngine` logic but focuses on granular operations.

**Methods:**
- `__init__(chunk_store: DiskChunkStore, agent: SummarizationAgent)`: Injection.
- `get_node(node_id: str) -> SummaryNode`: Retrieves a node from the store.
- `refine_node(node_id: str, instruction: str) -> SummaryNode`:
    1.  **Retrieve:** Fetches the node.
    2.  **Strategy Swap:** Temporarily sets the agent's strategy to `RefinementStrategy`.
    3.  **Generate:** Calls `agent.summarize(text=node.text, context={'instruction': instruction})`.
    4.  **Update:** Writes the new text back to the node, sets `is_user_edited=True`, and appends the instruction to `refinement_history`.
    5.  **Persist:** Saves the updated node to the DB.

### 3.2. RefinementStrategy (Prompt)

A strategy that rewrites existing text based on instructions.
- **Prompt Template:**
  ```text
  You are an expert editor. Rewrite the following text according to the user's instruction.
  Original Text: {text}
  Instruction: {instruction}
  Rewritten Text:
  ```
- **Parsing:** Returns `{'summary': rewritten_text}`.

### 3.3. Database Concurrency (Context Managers)

SQLite is file-based and supports limited concurrency. To prevent "database is locked" errors when the UI and background tasks (or multiple UI threads) access it:
- **Connection Strategy:** Open a new connection for *every* logical operation (or set of operations within a transaction) using a context manager.
- **Locking:** Use `timeout=10` (or higher) to allow waiting for the lock.
- **WAL Mode:** Enable Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) to allow simultaneous readers and one writer.

**`src/matome/utils/db.py` Example:**

```python
@contextmanager
def get_db_connection(db_path: str):
    conn = sqlite3.connect(db_path, timeout=20.0)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

## 4. Implementation Approach

This cycle focuses on backend stability under concurrent load.

### Step 1: Implement RefinementStrategy
In `src/matome/agents/strategies.py`, add the `RefinementStrategy` class. Ensure `format_prompt` uses the instruction from the `context` dictionary.

### Step 2: Audit & Refactor DiskChunkStore
Review `src/matome/engines/raptor.py` (or wherever `DiskChunkStore` lives).
- Replace any persistent `self.conn` with per-method connections using the context manager from Step 3.3.
- Ensure `get_node` and `save_node` are atomic.

### Step 3: Implement InteractiveRaptorEngine
Create `src/matome/engines/interactive.py`.
- Implement `refine_node`.
- **Crucial:** Ensure that `metadata` is correctly merged. Do not overwrite the entire metadata object; update only specific fields (`is_user_edited`, `refinement_history`).

### Step 4: Verify Thread Safety
Create a script that spawns multiple threads to read/write to the DB using the new engine. If errors occur, adjust the timeout or connection handling.

## 5. Test Strategy

Testing focuses on ensuring data integrity and concurrency safety.

### 5.1. Unit Testing
**File:** `tests/engines/test_interactive.py`
- **Test Case 1: Refine Node Logic**
    - **Setup:** Mock agent and store.
    - **Action:** Call `refine_node("id", "Make shorter")`.
    - **Assertion:** Agent called with `RefinementStrategy`. Node text updated. Metadata updated (`is_user_edited=True`). History length increased.
- **Test Case 2: Missing Node**
    - **Action:** Call `refine_node` with invalid ID.
    - **Assertion:** Raises `KeyError` or returns sensible error.

### 5.2. Concurrency Testing
**File:** `tests/utils/test_db_concurrency.py`
- **Test Case 1: Concurrent Writes**
    - **Setup:** A shared DB file.
    - **Action:** Spawn 5 threads. Each thread updates a different node 100 times.
    - **Assertion:** No `OperationalError: database is locked`. All updates persist.
- **Test Case 2: Read while Write**
    - **Setup:** One writer thread (slow updates), multiple reader threads.
    - **Assertion:** Readers successfully retrieve data (potentially slightly stale, but no crash).
