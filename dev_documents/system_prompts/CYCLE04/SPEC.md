# Cycle 04: GUI Foundation (MVVM) - Specification

## 1. Summary

Cycle 04 is the first step in building the user-facing "Matome Canvas." We will lay the groundwork for the web application using the `Panel` library, structured strictly according to the Model-View-ViewModel (MVVM) pattern. This ensures that the UI code remains clean, testable, and separated from the underlying data logic.

The goal is to create a functional (read-only) viewer for the DIKW tree generated in previous cycles. Users will be able to launch the app, see the root "Wisdom" node, and navigate the tree structure via a sidebar or basic list view.

## 2. System Architecture

```text
src/
├── matome/
│   ├── ui/
│   │   ├── **app.py**              # CREATED: Entry point (panel serve)
│   │   ├── **view_model.py**       # CREATED: InteractiveSession
│   │   └── components/
│   │       ├── **sidebar.py**      # CREATED: Tree navigation widget
│   │       └── **main_view.py**    # CREATED: Node detail view
tests/
├── **test_view_model.py**          # CREATED: Test MVVM logic without UI
```

### Key Components

*   **`InteractiveSession` (ViewModel)**: A class inheriting from `param.Parameterized`. It holds the state (`current_node`, `tree_structure`) and exposes methods to modify it.
*   **`app.py` (View/App)**: The layout definition using `pn.template.MaterialTemplate` or similar. It binds widgets to the ViewModel parameters.

## 3. Design Architecture

### 3.1. InteractiveSession (ViewModel)

```python
import param
from matome.engines.interactive import InteractiveRaptorEngine
from domain_models.chunk import SummaryNode

class InteractiveSession(param.Parameterized):
    """
    Manages the state of the user's session.
    """
    # Dependencies
    engine = param.ClassSelector(class_=InteractiveRaptorEngine)

    # State
    root_id = param.String()
    current_node = param.ClassSelector(class_=SummaryNode, allow_None=True)
    is_loading = param.Boolean(default=False)

    # Actions
    def select_node(self, node_id: str):
        self.is_loading = True
        try:
            self.current_node = self.engine.get_node(node_id)
        finally:
            self.is_loading = False

    def load_tree(self):
        # Logic to find the root node (Wisdom)
        # ...
```

### 3.2. View Components (Panel)

The UI will be composed of reactive components.

```python
# pseudo-code for main_view.py
def render_main_view(session: InteractiveSession):
    title = pn.pane.Markdown(object=session.param.current_node.chunk_id) # Reacts to change
    content = pn.pane.Markdown(object=session.param.current_node.text)
    return pn.Column(title, content)
```

## 4. Implementation Approach

### Step 1: Initialize Panel App
1.  Create `src/matome/ui/app.py`.
2.  Set up a basic `pn.template.MaterialTemplate`.
3.  Add a "Load DB" button to initialize the engine.

### Step 2: Implement ViewModel
1.  Create `src/matome/ui/view_model.py`.
2.  Define `InteractiveSession` with `param`.
3.  Implement `load_tree` to fetch the root node from `DiskChunkStore`.

### Step 3: Build Navigation View
1.  Create `src/matome/ui/components/sidebar.py`.
2.  Use a `pn.widgets.Tree` or simple list to display the hierarchy.
3.  Bind the selection event to `session.select_node`.

### Step 4: Build Detail View
1.  Create `src/matome/ui/components/main_view.py`.
2.  Bind markdown panes to `session.current_node`.

## 5. Test Strategy

### 5.1. ViewModel Unit Tests

**`tests/test_view_model.py`**
*   **Test State Updates**:
    *   Initialize `InteractiveSession` with a mock engine.
    *   Call `session.select_node("id_1")`.
    *   Assert `session.current_node.id == "id_1"`.
    *   Assert `session.is_loading` toggles correctly (True -> False).

### 5.2. UI Smoke Tests

**Manual Verification**:
*   Run `python -m matome.ui.app`.
*   Open browser at `localhost:5006`.
*   Click a node in the sidebar.
*   Verify the main content updates to show the node's text.
*   Verify no console errors in browser or terminal.
