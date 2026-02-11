# Cycle 04: GUI Foundation (MVVM & Basic View) - Specification

## 1. Summary

Cycle 04 introduces the visual frontend of the system: the **Panel GUI**. This cycle focuses on laying the structural foundation for the application using the **Model-View-ViewModel (MVVM)** pattern. By separating the business logic (ViewModel) from the UI layout (View), we ensure that the codebase remains testable and maintainable as the complexity of the interface grows.

We will create the `InteractiveSession` class (ViewModel) which manages the application state (e.g., "Which document is loaded?", "Which node is selected?"). We will also create the initial `app.py` (View) which renders a basic tree structure and allows for rudimentary navigation. While the advanced "Semantic Zooming" features are reserved for Cycle 05, this cycle will deliver a functional, if plain, application where users can see their data.

## 2. System Architecture

### File Structure

```ascii
src/
├── matome/
│   ├── gui/
│   │   ├── **app.py**          # [NEW] Main Panel Application Entry Point
│   │   ├── **view_model.py**   # [NEW] InteractiveSession (State Management)
│   │   └── **components/**     # [NEW] Reusable UI Components
│   │       ├── __init__.py
│   │       └── tree_view.py    # Basic Tree Visualization
│   └── cli.py               # [MODIFIED] Add "gui" command
```

## 3. Design Architecture

### 3.1. ViewModel (`src/matome/gui/view_model.py`)

The `InteractiveSession` class acts as the bridge between the GUI and the `InteractiveRaptorEngine`. It uses the `param` library to create reactive properties that the View can watch.

```python
import param

class InteractiveSession(param.Parameterized):
    """ViewModel for the Matome GUI."""

    # State
    root_node_id = param.String(default=None)
    selected_node = param.ClassSelector(class_=SummaryNode, default=None)
    is_loading = param.Boolean(default=False)
    status_message = param.String(default="Ready")

    def __init__(self, engine: InteractiveRaptorEngine, **params):
        super().__init__(**params)
        self.engine = engine

    def load_document(self, path: str):
        """Loads the document tree."""
        # ... fetch root from engine ...
        self.root_node_id = root.id

    def select_node(self, node_id: str):
        """Updates the selected node."""
        self.selected_node = self.engine.get_node(node_id)
```

### 3.2. View (`src/matome/gui/app.py`)

The main application layout. It initializes the `InteractiveSession` and binds UI components to its parameters.

```python
import panel as pn

def create_app():
    # ... setup dependencies ...
    session = InteractiveSession(engine=...)

    # Layout
    sidebar = pn.Column(
        pn.pane.Markdown("# Matome 2.0"),
        pn.widgets.Button(name="Load Document", on_click=...)
    )

    main_area = pn.Column(
        # Bind the view to session.selected_node
        pn.bind(render_node_details, session.param.selected_node)
    )

    return pn.template.FastListTemplate(
        title="Matome 2.0",
        sidebar=[sidebar],
        main=[main_area]
    )
```

## 4. Implementation Approach

### Step 1: Implement ViewModel (`src/matome/gui/view_model.py`)
1.  Define the `InteractiveSession` class inheriting from `param.Parameterized`.
2.  Add parameters for state (`selected_node`, `is_loading`).
3.  Implement methods to interact with `InteractiveRaptorEngine` (`load_tree`, `select_node`).

### Step 2: Create Basic Components (`src/matome/gui/components/tree_view.py`)
1.  Create a simple function or class that takes a list of nodes and returns a `pn.Column` of buttons or text representing them.

### Step 3: Implement Main App (`src/matome/gui/app.py`)
1.  Initialize Panel extension (`pn.extension()`).
2.  Instantiate `InteractiveSession`.
3.  Create the layout using `pn.template.FastListTemplate`.
4.  Add a `serve()` function to launch the server.

### Step 4: Add CLI Command (`src/matome/cli.py`)
1.  Add a `gui` subcommand to `typer`.
2.  This command should call `matome.gui.app.serve()`.

## 5. Test Strategy

### Unit Testing (ViewModel)
*   **`tests/unit/test_view_model.py`**:
    *   Instantiate `InteractiveSession` with a mock engine.
    *   Call `session.select_node("N1")`.
    *   Assert that `session.selected_node` is updated correctly.
    *   Assert that `session.is_loading` toggles correctly during async operations.

### Smoke Testing (View)
*   **`tests/integration/test_gui_launch.py`**:
    *   Try to instantiate the `create_app()` function.
    *   Assert that it returns a valid Panel object (Template) without raising exceptions.
    *   (Note: Full GUI interaction testing is deferred to manual UAT or specialized tools).
