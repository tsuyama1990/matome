# Cycle 03: Interactive Backend

## 1. Summary

This cycle focuses on enabling the **"Interactive Refinement"** feature required for the GUI. Unlike the batch-oriented `RaptorEngine` which processes the entire tree at once, the new `InteractiveRaptorEngine` must support random access and granular updates to individual nodes.

Crucially, because the CLI (batch process) and GUI (interactive process) might access the same SQLite database concurrently (or even multiple GUI sessions), we must enforce strict thread safety and transaction management in `DiskChunkStore`.

## 2. System Architecture

We introduce a new engine wrapper and harden the storage utility.

```ascii
src/matome/
├── engines/
│   └── **interactive_raptor.py** # [NEW] Controller for single-node operations
├── utils/
│   └── **store.py**            # [MOD] Add thread-safe context managers
└── agents/
    └── **strategies.py**       # [MOD] Add RefinementStrategy
```

### Files to Modify/Create

1.  **`src/matome/utils/store.py`**
    *   **Action**: Ensure `DiskChunkStore` uses context managers (`with sqlite3.connect(...)`) for all operations to handle locking correctly. Add methods for single-node retrieval and update.
2.  **`src/matome/agents/strategies.py`**
    *   **Action**: Implement `RefinementStrategy`.
        *   **Prompt**: "Here is the original text: {original}. Here is the user's instruction: {instruction}. Rewrite the text."
3.  **`src/matome/engines/interactive_raptor.py`**
    *   **Action**: Create `InteractiveRaptorEngine`.
        *   **Method**: `refine_node(node_id: str, instruction: str) -> SummaryNode`

## 3. Design Architecture

### 3.1. InteractiveRaptorEngine

This class acts as the API for the GUI. It orchestrates the refinement process.

*   **Dependencies**: `DiskChunkStore`, `SummarizationAgent`.
*   **Logic**:
    1.  Retrieve the target node from `store`.
    2.  Instantiate `RefinementStrategy` with the user's instruction.
    3.  Call `agent.summarize(original_text, strategy=refinement_strategy)`.
    4.  Update the node's text and metadata (`is_user_edited=True`, `refinement_history.append(instruction)`).
    5.  Save the updated node back to `store`.

### 3.2. DiskChunkStore Concurrency

SQLite supports concurrent reads but only one writer. To prevent `OperationalError: database is locked`:

*   **Read Operations**: Can be concurrent. Use strictly read-only connections if possible, or short-lived connections.
*   **Write Operations**: Must be atomic. Use `with connection:` to ensure commits/rollbacks. Set a reasonable `timeout` (e.g., 10s) to wait for locks.

## 4. Implementation Approach

1.  **Harden Store**: Refactor `DiskChunkStore` to ensure all DB access is wrapped in context managers. Add `get_node(id)` and `update_node(node)` methods.
2.  **Implement Strategy**: Create `RefinementStrategy` in `strategies.py`. It needs to accept the `instruction` as context during initialization or `format_prompt`.
3.  **Create Engine**: Implement `InteractiveRaptorEngine`.
    *   *Note*: The engine needs an `EmbeddingService` if refinement changes the embedding (optional for now, but good practice to re-embed). Let's assume we re-embed to keep the tree consistent.

## 5. Test Strategy

### 5.1. Unit Testing
*   **Refinement Logic**: Test that `InteractiveRaptorEngine.refine_node` correctly updates the node's text and metadata (history, edited flag).
*   **Strategy**: Test that `RefinementStrategy` incorporates the user instruction into the prompt.

### 5.2. Integration Testing (Concurrency)
*   **Torture Test**: Create a script that spawns multiple threads.
    *   Thread A: Continuously reads nodes.
    *   Thread B: Continuously updates nodes.
    *   **Success**: No crashes or database corruption. The operations should eventually succeed (handling timeouts/retries).
