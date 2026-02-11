# Cycle 04 Specification: GUI Foundation (MVVM)

## 1. Summary

Cycle 04 marks the transition from backend logic to frontend visualization. We will construct the foundational Graphical User Interface (GUI) using the **Panel** framework. The goal is to provide a user-friendly way to navigate the DIKW tree generated in Cycle 02 and interact with the controller built in Cycle 03.

To ensure the code remains clean and maintainable, we will strictly adhere to the **Model-View-ViewModel (MVVM)** pattern.
-   **Model**: The `SummaryNode` objects and the `InteractiveRaptorEngine` (data source).
-   **ViewModel**: A new class `InteractiveSession` that holds the *state* of the UI (e.g., "Which node is currently selected?", "Is the refinement panel open?").
-   **View**: The Panel layout definitions (`app.py` and components) that bind to the ViewModel.

By the end of this cycle, we will have a functional (read-only) application that can load a `chunks.db` and display the "Wisdom" root node. Navigation and Refinement will be fully implemented in Cycle 05, but the UI skeleton and state management will be established here.

## 2. System Architecture

### 2.1. File Structure

```ascii
matome/
├── src/
│   ├── matome/
│   │   ├── interface/
│   │   │   ├── __init__.py
│   │   │   ├── **app.py**          # CREATE: Main application entry point
│   │   │   ├── **session.py**      # CREATE: The ViewModel
│   │   │   └── **components/**     # CREATE: UI Component directory
│   │   │       ├── __init__.py
│   │   │       └── **canvas.py**   # CREATE: Tree visualization component
│   │   └── cli.py                  # MODIFY: Add `matome canvas` command
├── tests/
│   └── unit/
│       └── **test_viewmodel.py**   # CREATE: Test state transitions
└── pyproject.toml
```

### 2.2. Component Details

#### `src/matome/interface/session.py` (The ViewModel)
This class inherits from `param.Parameterized`. It is the heart of the UI logic.
-   **Parameters**:
    -   `selected_node`: The `SummaryNode` currently in focus.
    -   `root_node`: The cached Root Node.
    -   `is_loading`: Boolean flag for spinners.
-   **Methods**:
    -   `load_tree()`: Fetches initial data from the Engine.
    -   `select_node(node_id)`: Updates `selected_node`.

#### `src/matome/interface/components/canvas.py` (The View)
A collection of functions or classes that return Panel objects (e.g., `pn.Column`, `pn.Card`).
-   `render_node_card(node)`: Returns a card displaying the node's text and metadata.
-   `render_tree_view(root)`: Returns the hierarchical view (initially just the root).

#### `src/matome/interface/app.py` (The Application)
The entry point that assembles the components.
-   Instantiates `InteractiveRaptorEngine`.
-   Instantiates `InteractiveSession`.
-   Defines the main template (Sidebar + Main Area).
-   Serves the app.

## 3. Design Architecture

### 3.1. MVVM Pattern with Panel

Panel's reactive programming model is perfect for MVVM.
1.  **State**: Defined in `InteractiveSession` using `param`.
2.  **Binding**: The View functions use `@param.depends('session.selected_node')` to automatically re-run whenever the selection changes.

```python
class InteractiveSession(param.Parameterized):
    selected_node = param.ClassSelector(class_=SummaryNode, allow_None=True)

    def __init__(self, engine):
        self.engine = engine
        ...

# In canvas.py
def node_detail_view(session):
    @param.depends(session.param.selected_node)
    def _view(node):
        if not node:
            return pn.pane.Markdown("Select a node...")
        return pn.Card(node.text, title=f"Level: {node.metadata.dikw_level}")
    return pn.panel(_view)
```

### 3.2. Layout Strategy

We will use a standard "Master-Detail" or "Pyramid" layout.
-   **Top**: App Header ("Matome 2.0").
-   **Left/Center**: The **Canvas** (Tree Visualization).
    -   Wisdom (Root) at the top.
    -   Drill-down branches below (implemented in Cycle 05, represented as placeholders now).
-   **Right/Bottom**: The **Detail Panel** (Refinement Chat).
    -   Shows full text of selected node.
    -   Shows metadata.
    -   (Cycle 05: Chat input).

## 4. Implementation Approach

### Step 1: Implement `src/matome/interface/session.py`
1.  Import `param` and `InteractiveRaptorEngine`.
2.  Define the class.
3.  Implement `load_initial_state()`: Use the engine to fetch the root node and set it as `selected_node`.

### Step 2: Implement `src/matome/interface/components/canvas.py`
1.  Create basic renderers.
2.  `render_wisdom(node)`: A large, centered card for the root node.
3.  `render_detail(node)`: A structured view showing all metadata fields.

### Step 3: Implement `src/matome/interface/app.py`
1.  Setup `typer` command in `cli.py` to launch this app: `matome canvas [db_path]`.
2.  In `app.py`, use `pn.template.MaterialTemplate` or `FastListTemplate`.
3.  Wire the ViewModel to the components.
4.  Call `.servable()` on the template.

## 5. Test Strategy

### 5.1. Unit Testing Approach (Min 300 words)
Since we are using MVVM, we can test the UI logic *without* launching a browser.

**`tests/unit/test_viewmodel.py`**:
-   **Mocking**: Mock the `InteractiveRaptorEngine`.
-   **Test Initialization**:
    -   Instantiate `InteractiveSession`.
    -   Call `load_tree()`.
    -   Assert `session.root_node` is set to the mocked root.
    -   Assert `session.selected_node` is set (or None, depending on design).
-   **Test Selection**:
    -   Call `session.select_node("dummy_id")`.
    -   Assert `session.selected_node.id` == "dummy_id".
    -   Assert any dependent flags (e.g., `is_detail_open`) update correctly.

### 5.2. Integration/Manual Testing (Min 300 words)
UI testing is best done visually at this stage.

**`tests/manual/C04_ui_smoke_test.md`**:
-   **Steps**:
    1.  Generate a DB using `matome run --mode dikw`.
    2.  Run `matome canvas results/chunks.db`.
    3.  Open browser (localhost:5006).
-   **Checklist**:
    -   [ ] Does the app load without error?
    -   [ ] Is the "Wisdom" node visible at the top?
    -   [ ] Does clicking a node (if clickable) update the detail view? (Even if just placeholder).
    -   [ ] Is the styling consistent (Material/Fast design)?
