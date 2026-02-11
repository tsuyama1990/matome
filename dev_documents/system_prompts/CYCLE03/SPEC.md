# Cycle 03: Interactive Engine Backend

## 1. Summary

Cycle 03 focuses on transforming the system from a batch processor into an interactive engine capable of supporting a GUI. The existing `RaptorEngine` is designed for "build once" operations. We need a new controller, the `InteractiveRaptorEngine`, that allows users to query specific parts of the tree and refine individual nodes without reprocessing the entire document.

Key requirements for this cycle include:
1.  **Random Access**: Efficiently retrieving a node and its children.
2.  **Granular Updates**: Rewriting a single node based on user instructions (Refinement).
3.  **Concurrency Safety**: Ensuring that simultaneous reads (from the UI) and writes (from the engine) do not corrupt the SQLite database.

## 2. System Architecture

We will introduce a new engine module and enhance the storage utility.

### File Structure
```
src/
├── matome/
│   ├── agents/
│   │   └── **strategies.py**  # Modify: Add RefinementStrategy
│   ├── engines/
│   │   └── **interactive.py** # Create: InteractiveRaptorEngine
│   └── utils/
│       └── **store.py**       # Modify: Add thread-safe locking
```

## 3. Design Architecture

### 3.1. Interactive Engine (`src/matome/engines/interactive.py`)

The `InteractiveRaptorEngine` acts as a facade over the `DiskChunkStore` and `SummarizationAgent`.

```python
class InteractiveRaptorEngine:
    def __init__(self, store: DiskChunkStore, agent: SummarizationAgent, embedder: EmbeddingService):
        ...

    def get_node(self, node_id: str) -> SummaryNode:
        """Retrieves a node by ID."""
        ...

    def get_children(self, node_id: str) -> list[SummaryNode]:
        """Retrieves child nodes for navigation."""
        ...

    def refine_node(self, node_id: str, instruction: str) -> SummaryNode:
        """
        Regenerates a node's summary based on a user instruction.
        1. Retrieve the node.
        2. Retrieve its source text (children summaries or chunks).
        3. Use RefinementStrategy with the instruction.
        4. Generate new text.
        5. Update embedding.
        6. Update DB (and set is_user_edited=True).
        """
        ...
```

### 3.2. Refinement Strategy (`src/matome/agents/strategies.py`)

We need a strategy that takes an existing summary and a user instruction.

```python
class RefinementStrategy(PromptStrategy):
    def __init__(self, instruction: str):
        self.instruction = instruction

    def format_prompt(self, text: str, existing_summary: str | None = None) -> str:
        # Prompt: "Here is the original text: {text}.
        # The user wants to rewrite the summary with this instruction: {instruction}.
        # Please generate the new summary."
        ...
```

### 3.3. Thread-Safe Storage (`src/matome/utils/store.py`)

SQLite supports concurrent reads but only one write. We must ensure that our `DiskChunkStore` handles this gracefully, especially if the GUI (running in a separate thread/process) tries to read while the engine is writing.

- **Approach**: Use a thread-safe lock (e.g., `threading.Lock` or `filelock`) around write operations.
- **Connection Handling**: Ensure a fresh cursor is used or the connection is strictly managed within a `with` block.

## 4. Implementation Approach

1.  **Implement Strategy**:
    - Add `RefinementStrategy` to `src/matome/agents/strategies.py`.

2.  **Enhance Store**:
    - Add a `_lock` attribute to `DiskChunkStore`.
    - Wrap `add_node`, `update_node`, `add_chunks` with `with self._lock:`.
    - Ensure `sqlite3` is opened with `check_same_thread=False` if we share connections (or create new connections per thread).

3.  **Implement Engine**:
    - Create `InteractiveRaptorEngine`.
    - Implement `refine_node`:
        - Fetch node.
        - Construct prompt using `RefinementStrategy`.
        - Call `agent.summarize`.
        - Re-embed the new text.
        - `store.update_node(node)`.

## 5. Test Strategy

### Unit Testing
- **Refinement Strategy**:
    - Test that the prompt includes the user's instruction.

### Integration Testing
- **Interactive Engine**:
    - Initialize engine with a populated store.
    - Call `refine_node("some_id", "Make it shorter")`.
    - Verify that the node in the store has updated text.
    - Verify `node.metadata.is_user_edited` is True.
    - Verify `node.metadata.refinement_history` contains "Make it shorter".

### Concurrency Testing
- **Thread Safety**:
    - Create a test with 2 threads.
    - Thread A: Continuously reads nodes.
    - Thread B: Continuously updates nodes.
    - Verify no `sqlite3.OperationalError: database is locked` occurs (or is handled/retried).
