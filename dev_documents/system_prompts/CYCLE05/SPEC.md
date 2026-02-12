# Cycle 05 Specification: Semantic Zooming & Polish

## 1. Summary

Cycle 05 is the final implementation phase, focusing on the core value proposition: **Semantic Zooming** and **Source Traceability**. In this cycle, we connect the UI components from Cycle 04 to the hierarchical data structure built in Cycles 02-03. Users will be able to "zoom in" from a high-level Wisdom node to its supporting Knowledge nodes, and finally down to the raw Data chunks. This cycle also includes UI polishing to ensure a professional and intuitive user experience.

## 2. System Architecture

We will enhance the engine and UI to support traversal and context-aware navigation.

```ascii
src/
├── matome/
│   ├── engines/
│   │   └── interactive.py   # [MODIFIED] Add Traversal Methods
│   └── ui/
│       ├── session.py       # [MODIFIED] Add Zoom Logic
│       └── canvas.py        # [MODIFIED] Add Breadcrumbs & Source View
```

**New Logic:**
- **Traversal:** `InteractiveRaptorEngine` gains methods to traverse the tree (get children, get source).
- **Zooming:** `InteractiveSession` gains state for tracking the current view context (navigation history).
- **UI:** `MatomeCanvas` displays breadcrumbs and a source text modal.

## 3. Design Architecture

### 3.1. InteractiveRaptorEngine (Traversal)

The engine needs to navigate the graph.
- **`get_children(node_id: str) -> List[SummaryNode]`**: Returns the immediate children of a node.
- **`get_source_chunks(node_id: str) -> List[str]`**: Recursively traverses down the tree to find all leaf nodes (DIKW=DATA) associated with the given node.
    - **Optimization:** Use an iterative approach (stack) rather than recursion to avoid `RecursionError` on deep trees.

### 3.2. InteractiveSession (Zoom State)

The session tracks "where" the user is in the hierarchy.
- **`view_context`**: `param.ClassSelector(SummaryNode)`: The "parent" node currently being zoomed into. If `None`, we are at the Root (Wisdom) level.
- **`breadcrumbs`**: `param.List(SummaryNode)`: A stack representing the navigation path.
- **`zoom_in(node: SummaryNode)`**:
    1.  Push current `view_context` to `breadcrumbs`.
    2.  Set `view_context` to `node`.
    3.  Update `current_level` to the child's level (e.g., WISDOM -> KNOWLEDGE).
    4.  Fetch children nodes to display.
- **`zoom_out()`**:
    1.  Pop the last node from `breadcrumbs`.
    2.  Set `view_context` to that node.
    3.  Update `current_level` accordingly.

### 3.3. MatomeCanvas (Advanced UI)

- **Breadcrumb Bar:**
    - A horizontal list of links: "Home > Wisdom: [Summary] > Knowledge: [Summary]".
    - Clicking a breadcrumb calls `session.jump_to(breadcrumb_node)`.
- **Source Modal:**
    - A button "View Source" on the `NodeDetailView`.
    - Clicking it opens a modal (using `pn.Template` or `pn.Column` in a popup).
    - The modal calls `session.engine.get_source_chunks(node.id)` and displays the text.
- **Styling:**
    - Use specific colors/borders for each DIKW level (e.g., Gold for Wisdom, Blue for Knowledge).

## 4. Implementation Approach

This cycle integrates everything.

### Step 1: Engine Traversal Logic
In `src/matome/engines/interactive.py`, implement `get_children` (query children IDs) and `get_source_chunks` (BFS/DFS traversal).

### Step 2: Session Zoom Logic
In `src/matome/ui/session.py`, implement `zoom_in`, `zoom_out`, and `jump_to`. Ensure strict state transitions (e.g., cannot zoom in on a Leaf node).

### Step 3: UI Enhancements
In `src/matome/ui/canvas.py`:
- Add the Breadcrumb component at the top.
- Update the main list view to bind to `session.view_context`. If context is None, show Roots. If context is a Node, show its Children.
- Add the "View Source" button and modal logic.

### Step 4: Final Polish
Add CSS classes or Panel styles. Ensure the app looks cohesive.

## 5. Test Strategy

Testing focuses on navigation correctness.

### 5.1. Unit Testing (Engine)
**File:** `tests/engines/test_traversal.py`
- **Test Case 1: Child Retrieval**
    - **Setup:** Create Mock Tree (Root -> A, B).
    - **Action:** Call `get_children(Root)`.
    - **Assertion:** Returns [A, B].
- **Test Case 2: Source Retrieval**
    - **Setup:** Create Mock Tree (Root -> A -> Leaf1).
    - **Action:** Call `get_source_chunks(Root)`.
    - **Assertion:** Returns [Leaf1].

### 5.2. Functional Testing (Zoom)
**File:** `tests/ui/test_zoom.py`
- **Test Case 1: Zoom In**
    - **Action:** Call `session.zoom_in(node)`.
    - **Assertion:** `breadcrumbs` has 1 item. `view_context` is `node`.
- **Test Case 2: Zoom Out**
    - **Action:** Call `session.zoom_out()`.
    - **Assertion:** `breadcrumbs` is empty. `view_context` is None.
