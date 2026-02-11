# Cycle 03 Specification: Interactive Engine & Concurrency

## 1. Summary

Cycle 03 is the bridge between the backend generation logic (Cycle 02) and the frontend user experience (Cycle 04). Its primary goal is to create a robust, thread-safe controller layer that allows the GUI to interact with the database and the LLM in real-time.

Currently, the `RaptorEngine` is designed for batch processing: it starts, runs to completion, and exits. The GUI, however, requires an "Interactive Engine" that can stay alive, serve read requests for the tree visualization, and handle write requests (refinements) concurrently.

We will introduce the `InteractiveRaptorEngine` (or `RaptorController`), which wraps the core components and exposes a high-level API for the UI. Simultaneously, we must harden the `DiskChunkStore` (SQLite wrapper). Since the UI thread will be reading from the DB while background threads might be updating it (during refinement), we must enable SQLite's Write-Ahead Logging (WAL) mode and enforce strict transaction management to prevent "database locked" errors.

## 2. System Architecture

### 2.1. File Structure

```ascii
matome/
├── src/
│   ├── matome/
│   │   ├── engines/
│   │   │   ├── **interactive.py** # CREATE: The Controller for the GUI
│   │   │   └── raptor.py
│   │   └── utils/
│   │       └── **store.py**       # MODIFY: Add context managers and WAL mode
├── tests/
│   ├── integration/
│   │   └── **test_concurrency.py** # CREATE: Test multi-threaded DB access
│   └── unit/
│       └── **test_interactive_engine.py** # CREATE: Test controller API
└── pyproject.toml
```

### 2.2. Component Details

#### `src/matome/utils/store.py` (Modification)
-   **WAL Mode**: In `__init__`, execute `PRAGMA journal_mode=WAL;` to enable better concurrency.
-   **Context Manager**: Implement a `get_session()` context manager that yields a cursor/connection and ensures commits/rollbacks happen automatically.
-   **Row Factory**: Ensure queries return dictionary-like objects (already likely done, but verify) for easier Pydantic parsing.

#### `src/matome/engines/interactive.py` (New)
This class acts as the API Gateway for the Frontend.
-   **Responsibilities**:
    -   Hold references to `DiskChunkStore` and `SummarizationAgent`.
    -   Provide read methods: `get_root()`, `get_children(node_id)`, `get_node(node_id)`.
    -   Provide write methods: `refine_node(node_id, user_instruction)`.
    -   Handle exceptions gracefully (so the UI doesn't crash).

## 3. Design Architecture

### 3.1. Interactive Engine API

The `InteractiveRaptorEngine` decouples the UI from the DB schema.

```python
class InteractiveRaptorEngine:
    def __init__(self, db_path: str, agent: SummarizationAgent):
        self.store = DiskChunkStore(db_path)
        self.agent = agent

    def get_tree_structure(self) -> Dict[str, List[SummaryNode]]:
        """
        Returns a simplified adjacency list or nested structure
        optimized for the UI's tree viewer.
        """
        ...

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        1. Retrieve node from DB.
        2. Construct a refinement prompt (using agent).
        3. Call LLM.
        4. Update node.text and node.metadata (is_user_edited=True).
        5. Persist to DB.
        6. Return updated node.
        """
        ...
```

### 3.2. Concurrency Model

SQLite is serverless, so concurrency is managed via file locks.
-   **WAL Mode**: Allows one writer and multiple readers simultaneously. This is perfect for our use case (User reading the tree while occasionally writing a refinement).
-   **Connection Management**: Each thread (UI thread vs. Background worker) should ideally have its own connection, or we use a thread-local storage strategy. However, for this scale, creating a new connection per request (or using a pooled wrapper) inside the context manager is the safest approach to avoid "SQLite objects created in a thread can only be used in that same thread" errors.

## 4. Implementation Approach

### Step 1: Refactor `DiskChunkStore`
1.  Modify `__init__`: Add `self.conn.execute("PRAGMA journal_mode=WAL;")`.
2.  Audit all `execute` calls. Ensure they are wrapped in `with self.conn:` or equivalent transaction blocks.
3.  Ensure thread safety. If `DiskChunkStore` is shared across threads, the connection object needs care. **Better Strategy**: `DiskChunkStore` holds the *path*, and creates a new connection for each public method call (or uses a `threading.local` connection). Given the low traffic, opening/closing per method is acceptable overhead and maximally safe.

### Step 2: Implement `InteractiveRaptorEngine`
1.  Implement `get_root` and `get_children`. These are simple SELECT queries via the store.
2.  Implement `refine_node`.
    -   Fetch the node.
    -   Construct prompt: "Original text: {text}. User instruction: {instruction}. Rewrite."
    -   Call `self.agent.llm`.
    -   Update the node object.
    -   Call `store.update_node(node)`.

## 5. Test Strategy

### 5.1. Unit Testing Approach (Min 300 words)
**`tests/unit/test_interactive_engine.py`**:
-   **Mocking**: Mock the `DiskChunkStore` and `SummarizationAgent`. We don't want real DB or LLM calls here.
-   **Test `refine_node`**:
    -   Setup: Mock store returns a node "Original".
    -   Action: Call `refine_node(id, "Make it shorter")`.
    -   Assert: Agent was called with a prompt containing "Make it shorter".
    -   Assert: Store `update_node` was called with the new text.
    -   Assert: The returned node has `is_user_edited=True`.
-   **Test `get_tree_structure`**:
    -   Setup: Mock store returns a list of nodes with parent/child relationships.
    -   Action: Call `get_tree_structure`.
    -   Assert: The returned dictionary correctly represents the hierarchy (Root -> Knowledge -> Action).

### 5.2. Integration Testing Approach (Min 300 words)
**`tests/integration/test_concurrency.py`**:
-   **Objective**: Prove that the GUI won't freeze or crash if the user clicks around while a refinement is saving.
-   **Setup**: Create a real SQLite DB with WAL enabled. Populate with dummy data.
-   **Scenario**:
    -   Thread A (Reader): In a loop, read the Root Node every 10ms.
    -   Thread B (Writer): In a loop, update a Leaf Node every 50ms (simulating a slow LLM generation + write).
    -   Run for 5 seconds.
    -   **Pass Criteria**: Zero exceptions raised. Data read by Thread A eventually reflects writes by Thread B.

**`tests/integration/test_refinement_flow.py`**:
-   **Objective**: End-to-End refinement.
-   **Setup**: Real Store, Mock Agent (returning "Refined Text").
-   **Action**: Call `engine.refine_node`.
-   **Verification**: Re-instantiate the store (simulating app restart) and fetch the node. Verify "Refined Text" is persisted.
