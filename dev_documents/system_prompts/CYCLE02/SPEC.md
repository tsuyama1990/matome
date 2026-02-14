# Cycle 02 Specification: Interactive Engine & Backend Persistence

## 1. Summary

This cycle focuses on building the backend infrastructure required for the interactive "Knowledge Installation" experience. While Cycle 01 established the static generation logic, Cycle 02 introduces the `InteractiveRaptorEngine`—a specialized controller designed for granular, user-driven updates.

The key challenge here is state management and concurrency. Unlike the batch process that builds a tree once, the interactive engine must handle targeted updates ("Refine this node") while the GUI might be reading data simultaneously. We will implement robust SQLite concurrency controls (WAL mode, Context Managers) and a locking mechanism to preserve user edits. By the end of this cycle, we will have a Python API capable of receiving a "Refine" command and updating a specific node in the database without corrupting the tree structure.

## 2. System Architecture

### File Structure (ASCII Tree)

```
matome/
├── src/
│   ├── matome/
│   │   ├── engines/
│   │   │   ├── **interactive.py**  # [Implement] The core InteractiveRaptorEngine class
│   │   │   └── raptor.py       # [Refactor] Extract shared logic if necessary
│   │   ├── utils/
│   │   │   └── store.py        # [Refactor] Add Context Managers & WAL mode
│   │   └── agents/
│   │   │   └── **strategies.py**   # [Update] Add RefinementStrategy wrapper
│   └── tests/
│       └── integration/
│           └── **test_interactive.py** # [Create] Tests for single-node refinement
```

### Key Components

1.  **InteractiveRaptorEngine:**
    Located in `src/matome/engines/interactive.py`.
    -   **Responsibility:** Orchestrate user-initiated updates.
    -   **Methods:**
        -   `get_node(node_id)`: Retrieve a node.
        -   `refine_node(node_id, instruction)`: The core method.
        -   `_lock_node(node_id)`: Mark a node as `is_user_edited`.

2.  **RefinementStrategy (Decorator Pattern):**
    Located in `src/matome/agents/strategies.py`.
    -   Wraps an existing strategy (e.g., `WisdomStrategy`) and injects the user's instruction into the prompt.
    -   Example Prompt: "Original Context... User Instruction: 'Make it funnier'... Output: ..."

3.  **DiskChunkStore (Concurrency Upgrade):**
    Located in `src/matome/utils/store.py`.
    -   **Upgrade:** Enable SQLite WAL (Write-Ahead Logging) mode (`PRAGMA journal_mode=WAL;`).
    -   **Upgrade:** Use a `contextlib.contextmanager` for database connections to ensure they are closed/committed even if errors occur.

## 3. Design Architecture

### Interactive Logic Flow

```python
class InteractiveRaptorEngine:
    def __init__(self, store: DiskChunkStore, agent: SummarizationAgent):
        self.store = store
        self.agent = agent

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        # 1. Fetch Node & Children
        node = self.store.get_node(node_id)
        children = self.store.get_children(node.children_indices)

        # 2. Determine Strategy
        base_strategy = self._get_strategy_for_level(node.level)
        refinement_strategy = RefinementStrategy(base_strategy, instruction)

        # 3. Call Agent
        new_text = self.agent.summarize(children, strategy=refinement_strategy)

        # 4. Update Node
        node.text = new_text
        node.metadata.is_user_edited = True
        node.metadata.refinement_history.append(instruction)

        # 5. Persist
        self.store.update_node(node)
        return node
```

### Data Consistency
-   **Atomic Updates:** SQLite's atomic commit ensures that a node update is all-or-nothing.
-   **Locking:** The `is_user_edited` flag in metadata prevents future batch processes (if any) from overwriting user customizations.

## 4. Implementation Approach

1.  **Step 1: Enhance DiskChunkStore**
    -   Modify `__init__` to execute `PRAGMA journal_mode=WAL;`.
    -   Implement `update_node(node: SummaryNode)` method using `UPDATE` SQL statement.
    -   Ensure `get_node` and `update_node` use a context manager for the connection.

2.  **Step 2: Implement RefinementStrategy**
    -   Create a class `RefinementStrategy(PromptStrategy)`.
    -   It takes a `base_strategy` and `instruction` in `__init__`.
    -   `format_prompt` calls `base_strategy.format_prompt` and appends "USER INSTRUCTION: {instruction}".

3.  **Step 3: Implement InteractiveRaptorEngine**
    -   Create the class structure.
    -   Implement `refine_node` logic as described above.
    -   Add error handling (e.g., if node not found).

4.  **Step 4: Integration Test**
    -   Create a test script that:
        1.  Creates a dummy node in the DB.
        2.  Initializes `InteractiveRaptorEngine`.
        3.  Calls `refine_node` with a mock agent.
        4.  Verifies the DB is updated.

## 5. Test Strategy

### Unit Testing Approach (Min 300 words)
-   **Store Concurrency:** We will create a test that spawns two threads: one continuously reading a node, and another updating it. We assert that no "Database Locked" errors occur and that reads eventually see the write (Thanks to WAL mode).
-   **Refinement Logic:** We will mock the `SummarizationAgent` to return "Refined Text". We will call `refine_node` and assert that the returned node has the new text and that `is_user_edited` is True.
-   **Strategy Decorator:** We will test `RefinementStrategy` to ensure it correctly combines the base prompt with the user instruction.

### Integration Testing Approach (Min 300 words)
-   **Persistence:** We will create a `DiskChunkStore` on disk (not memory), add a node, close the store, reopen it, and verify the node exists. Then we perform an update via the Engine, close, reopen, and verify the update.
-   **Error Handling:** We will simulate a failure during the LLM call (e.g., raise Exception). We will verify that the database remains in its original state (Transaction Rollback).
