# Cycle 04: GUI Foundation (MVVM)

## 1. Summary

Cycle 04 focuses on building the reactive foundation for the **Matome Canvas** GUI. We will adopt the **Model-View-ViewModel (MVVM)** pattern using the `panel` and `param` libraries. This ensures a clean separation between the UI logic (ViewModel) and the visual representation (View), making the code testable and maintainable.

The goal is to create a functional "skeleton" of the application where the state changes in the backend (e.g., selecting a node) automatically trigger updates in the frontend components, even without the full styling and features of the final product.

## 2. System Architecture

We will introduce the UI module.

### File Structure
```
src/
├── matome/
│   ├── ui/
│   │   ├── **__init__.py**
│   │   ├── **session.py**    # Create: InteractiveSession (ViewModel)
│   │   └── **canvas.py**     # Create: MatomeCanvas (View)
```

## 3. Design Architecture

### 3.1. Interactive Session (ViewModel) (`src/matome/ui/session.py`)

The `InteractiveSession` class manages the state of the user's interaction. It inherits from `param.Parameterized` to leverage reactive programming.

```python
import param
from matome.domain_models.schema import SummaryNode
from matome.engines.interactive import InteractiveRaptorEngine

class InteractiveSession(param.Parameterized):
    # Reactive Parameters
    current_node = param.ClassSelector(class_=SummaryNode, allow_None=True)
    child_nodes = param.List(default=[])
    is_loading = param.Boolean(default=False)
    status_message = param.String(default="Ready")

    def __init__(self, engine: InteractiveRaptorEngine, root_node_id: str):
        super().__init__()
        self.engine = engine
        # Load initial state
        self.load_node(root_node_id)

    def load_node(self, node_id: str):
        """Updates current_node and fetches children."""
        self.is_loading = True
        self.status_message = f"Loading node {node_id}..."
        try:
            self.current_node = self.engine.get_node(node_id)
            self.child_nodes = self.engine.get_children(node_id)
            self.status_message = "Loaded."
        finally:
            self.is_loading = False
```

### 3.2. Matome Canvas (View) (`src/matome/ui/canvas.py`)

The `MatomeCanvas` is a `pn.viewable.Viewer` component that composes the UI. It observes the `InteractiveSession` and rebuilds or updates its widgets when parameters change.

```python
import panel as pn
from matome.ui.session import InteractiveSession

class MatomeCanvas(pn.viewable.Viewer):
    def __init__(self, session: InteractiveSession):
        self.session = session
        super().__init__()

    def __panel__(self):
        # Layout definition
        return pn.Column(
            self.header_view,
            pn.Row(
                self.sidebar_view,
                self.main_content_view
            )
        )

    @pn.depends("session.current_node")
    def main_content_view(self):
        if not self.session.current_node:
            return pn.pane.Markdown("No node selected.")
        return pn.Card(self.session.current_node.text, title="Current Node")
```

## 4. Implementation Approach

1.  **Implement ViewModel**:
    - Create `src/matome/ui/session.py`.
    - Define `InteractiveSession` with `param` fields.
    - Implement `load_node` logic connecting to the `InteractiveRaptorEngine`.

2.  **Implement View**:
    - Create `src/matome/ui/canvas.py`.
    - Implement basic layout with placeholders.
    - Use `@pn.depends` decorators to bind UI components to ViewModel state.

3.  **Launch Script**:
    - Create a temporary script `debug_gui.py` to launch the app: `pn.serve(MatomeCanvas(session))`.

## 5. Test Strategy

### Unit Testing
- **ViewModel Logic**:
    - Instantiate `InteractiveSession` with a mocked engine.
    - Call `session.load_node("test_id")`.
    - Assert `session.current_node` is updated.
    - Assert `session.child_nodes` is populated.
    - Assert `session.is_loading` toggles correctly (True -> False).

### Integration Testing (Headless)
- **Reactive Binding**:
    - We can test that the View updates without running a browser.
    - Instantiate `MatomeCanvas(session)`.
    - Update `session.current_node`.
    - Call `canvas.main_content_view()` manually and check if the returned Panel object contains the new text.
