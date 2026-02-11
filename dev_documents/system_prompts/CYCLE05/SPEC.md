# Cycle 05: Semantic Zooming & Refinement (Final Polish) - Specification

## 1. Summary

This final cycle completes the Matome 2.0 vision. We will integrate the `InteractiveRaptorEngine`'s refinement capabilities into the GUI, enabling users to rewrite nodes via a chat interface. Additionally, we will implement "Source Verification," allowing users to view the original text chunks linked to any summary node. This ensures trust and transparency.

## 2. System Architecture

We enhance the `interface` package with new interactive components.

```ascii
src/
├── matome/
│   ├── interface/
│   │   ├── viewmodel.py       # MODIFY: Add refinement & source logic
│   │   └── **components.py**  # MODIFY: Add ChatInterface, SourceViewer
│   └── ...
```

**Key Changes:**
1.  **`src/matome/interface/components.py`**:
    -   `RefinementChat`: A `pn.chat.ChatFeed` or text input area.
    -   `SourceViewer`: A collapsible pane or tab that displays the raw text of chunks associated with `selected_node`.
2.  **`src/matome/interface/viewmodel.py`**:
    -   Update `InteractiveSession` to handle `refine_node(instruction)` calls.
    -   Add `load_source()` logic to fetch leaf chunks for the selected node.

## 3. Design Architecture

### 3.1. Interactive Refinement Flow

1.  **User Action:** Selects a node in the Tree.
2.  **View:** Displays the node text.
3.  **User Action:** Types "Make this simpler" in the Chat box.
4.  **View:** Calls `session.refine_node("Make this simpler")`.
5.  **ViewModel:**
    -   Sets `is_processing = True`.
    -   Calls `engine.refine_node(selected_node.id, instruction)`.
    -   Receives updated `SummaryNode`.
    -   Updates `selected_node` with the new version.
    -   Sets `is_processing = False`.
6.  **View:** Automatically refreshes to show the new text.

### 3.2. Source Verification (Traceability)

Every `SummaryNode` has `children_indices`.
-   If children are chunks (L0), display them directly.
-   If children are SummaryNodes, we might need to recursively fetch *their* children until we hit chunks (or just show immediate children).
-   **Design Decision:** For "Source," show the *immediate* children text. If the user wants raw data, they drill down to the leaf level.

## 4. Implementation Approach

### Step 1: Implement Source Viewer
1.  In `InteractiveSession`, add `source_chunks = param.List(SummaryNode | Chunk)`.
2.  In `components.py`, create `SourceViewer` that iterates over `session.source_chunks` and displays them.
3.  Bind `load_source` to `selected_node` changes.

### Step 2: Implement Refinement Chat
1.  In `components.py`, add `RefinementChat` component.
2.  Use `pn.widgets.TextInput` and a "Send" button.
3.  On click, call `session.refine_node(input_value)`.

### Step 3: Polish & Assembly
1.  Combine Tree, Detail, Source, and Chat into a cohesive layout (e.g., specific tabs or side-by-side view).
2.  Ensure loading states (spinners) are visible during LLM calls.

## 5. Test Strategy

### 5.1. Integration Testing (GUI -> Engine)
-   **Refinement:**
    -   Mock the Engine to return a modified node immediately.
    -   Type into the Chat widget.
    -   Verify that the Detail View updates with the mock response.
-   **Source Loading:**
    -   Select a node.
    -   Verify `session.source_chunks` is populated.
    -   Verify `SourceViewer` displays the text of the children.

### 5.2. End-to-End User Acceptance
-   **Full Scenario:**
    -   Load a real document.
    -   Drill down to a specific "Action" node.
    -   Ask to "translate to Spanish".
    -   Verify the node becomes Spanish.
    -   Click "Show Source" and verify the English context is visible.
