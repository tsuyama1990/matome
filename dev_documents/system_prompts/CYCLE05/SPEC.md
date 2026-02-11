# Cycle 05: Semantic Zooming & Polish

## 1. Summary

This final cycle brings the "Knowledge Installation" vision to life by connecting the `InteractiveRaptorEngine` (Cycle 03) to the Panel GUI (Cycle 04).

We will implement the two core interactive features:
1.  **Semantic Zooming**: Users can click on a node to "drill down" into its children (e.g., Wisdom -> Knowledge).
2.  **Refinement**: Users can rewrite specific nodes using natural language instructions.

## 2. System Architecture

We will enhance the existing UI components and wire them to the backend engine.

```ascii
src/matome/
├── ui/
│   ├── **session.py**          # [MOD] Add refine_node() and zoom logic
│   └── **canvas.py**           # [MOD] Add Refinement UI and Child Navigation
```

### Files to Modify/Create

1.  **`src/matome/ui/session.py`**
    *   **Action**: Inject `InteractiveRaptorEngine`. Implement `refine_node(instruction)` and `zoom_into(child_id)`.
2.  **`src/matome/ui/canvas.py`**
    *   **Action**: Add UI controls for refinement (TextInput, Button) and navigation (Child List/Grid).

## 3. Design Architecture

### 3.1. InteractiveSession (ViewModel) Enhancements

*   **State**: Add `children` (list[SummaryNode]) parameter. This list updates whenever `current_node` changes.
*   **Methods**:
    *   `refine_node(instruction: str)`: Calls `engine.refine_node`, updates the DB, and refreshes `current_node` in-place.
    *   `zoom_into(node_id: str)`: Sets `current_node` to the selected child.
    *   `zoom_out()`: Sets `current_node` to the parent of the current node (requires parent tracking or DB query).

### 3.2. MatomeCanvas (View) Layout

*   **Main View**:
    *   **Top**: Breadcrumb navigation (Root > Node 1 > Node 1.2).
    *   **Center**: The `current_node` content (Markdown).
    *   **Bottom**: Refinement Interface.
        *   Input: "How should this be rewritten?"
        *   Button: "Refine".
    *   **Right/Bottom**: Children Grid.
        *   List of clickable cards representing `children`.
        *   Clicking a child triggers `session.zoom_into(child.id)`.

## 4. Implementation Approach

1.  **Backend Integration**: Pass `InteractiveRaptorEngine` to `InteractiveSession.__init__`.
2.  **Zoom Logic**: Implement `session.load_children()` which queries `DiskChunkStore` for children of `current_node.id`. Bind this to `current_node` updates.
3.  **Refinement Logic**: Implement `session.refine_node`. Ensure it handles the async nature of LLM calls (show loading spinner).
4.  **UI Components**:
    *   Use `pn.widgets.TextInput` and `pn.widgets.Button` for refinement.
    *   Use `pn.FlexBox` or `pn.GridBox` for displaying children.

## 5. Test Strategy

### 5.1. Unit Testing (ViewModel)
*   **Refinement**: Mock the engine. Call `session.refine_node("test")`. Assert engine was called and `current_node` updated.
*   **Zooming**: Mock the store. Call `session.zoom_into("child_id")`. Assert `current_node` is now the child.

### 5.2. User Acceptance Testing (Manual)
*   **Full Flow**:
    1.  Launch UI.
    2.  See Wisdom.
    3.  Click a child (Zoom In to Knowledge).
    4.  Refine the Knowledge node ("Make it simpler").
    5.  Verify the change persists.
    6.  Zoom further to Information/Action.
