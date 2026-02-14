# Cycle 05 Specification: Polish, Traceability & Final Release

## 1. Summary

The final cycle focuses on trust, usability, and completeness. A critical requirement for any AI system is traceability—users need to know *why* the AI generated a specific summary. We will implement a "Source Verification" feature that allows users to click a node and see the original text chunks that contributed to it.

Additionally, we will polish the UI, improve prompt engineering based on feedback from previous cycles, and create a comprehensive "Gold Master" tutorial using `marimo`. This tutorial will serve as both user documentation and an automated UAT script. Finally, we will prepare the repository for release with a complete `README.md` and cleaned-up code.

## 2. System Architecture

### File Structure (ASCII Tree)

```
matome/
├── src/
│   ├── matome/
│   │   ├── engines/
│   │   │   └── **interactive.py**  # [Modify] Add get_source_chunks method
│   │   ├── ui/
│   │   │   └── **canvas.py**       # [Modify] Add Source Viewer Modal
│   └── tutorials/
│       └── **UAT_AND_TUTORIAL.py** # [Create] Marimo notebook for End-to-End UAT
```

### Key Components

1.  **Traceability Engine:**
    Located in `src/matome/engines/interactive.py`.
    -   `get_source_chunks(node_id: str) -> list[Chunk]`:
        -   Recursively traverses the `children_indices` of the given node.
        -   Collects all leaf nodes (Level 0 Chunks).
        -   Returns them as a list of `Chunk` objects.

2.  **Source Viewer (UI):**
    Located in `src/matome/ui/canvas.py`.
    -   A "Show Source" button on the Node Detail panel.
    -   Clicking it opens a Modal or a toggleable area displaying the raw text of the contributing chunks.
    -   This provides the "Evidence" layer of the DIKW model.

3.  **Gold Master Tutorial:**
    Located in `tutorials/UAT_AND_TUTORIAL.py`.
    -   A Marimo notebook that:
        1.  Initializes the engine.
        2.  Loads a sample file.
        3.  Generates a tree (Mock Mode or Real).
        4.  Displays the tree structure programmatically.
        5.  Demonstrates refinement API.
        6.  Verifies assertions (UAT).

## 3. Design Architecture

### Traceability Logic

```python
    def get_source_chunks(self, node_id: str) -> list[Chunk]:
        """
        Retrieves all original text chunks that contributed to this summary node.
        Performs a BFS/DFS traversal down to Level 0.
        """
        node = self.store.get_node(node_id)
        if not node: return []

        # If node is already a chunk (unlikely in SummaryNode table, but possible in logic)
        # handle accordingly.

        # Traversal logic...
        # Collect chunk_ids
        # Fetch chunks from store
        return chunks
```

### UI Polish
-   **CSS Styling:** Apply a clean, professional theme (e.g., Material Design or simple dark mode).
-   **Responsiveness:** Ensure the layout works on smaller screens (if possible with Panel).
-   **Error Feedback:** gracefully handle network errors or empty states.

## 4. Implementation Approach

1.  **Step 1: Implement Traceability**
    -   Add `get_source_chunks` to `InteractiveRaptorEngine`.
    -   Optimize for performance (don't fetch full objects until leaves are found).

2.  **Step 2: Add UI Component**
    -   Add `pn.widgets.Button(name="Show Source")`.
    -   Bind click to `session.load_source_chunks(node_id)`.
    -   Display chunks in a scrollable `pn.Column`.

3.  **Step 3: Create Tutorial**
    -   Write `tutorials/UAT_AND_TUTORIAL.py`.
    -   Include "Quick Start," "Advanced Usage," and "Verification" sections.

4.  **Step 4: Final Cleanup**
    -   Run `ruff format`.
    -   Ensure all tests pass.
    -   Verify `README.md` is up to date.

## 5. Test Strategy

### Unit Testing Approach (Min 300 words)
-   **Traceability:** Create a known tree structure (Root -> Child1 -> [ChunkA, ChunkB]). Call `get_source_chunks(Root)`. Assert it returns [ChunkA, ChunkB].
-   **Performance:** Ensure traversal doesn't hang on deep trees (though max depth is usually low in RAPTOR).

### Integration Testing Approach (Min 300 words)
-   **Tutorial Verification:** The primary integration test for this cycle IS the `UAT_AND_TUTORIAL.py` file. Running it successfully from top to bottom confirms the entire system functions as expected.
-   **Mock Mode:** Ensure the tutorial can run in "Mock Mode" (without API keys) for CI/CD environments. This requires mocking the `SummarizationAgent` to return deterministic text.
