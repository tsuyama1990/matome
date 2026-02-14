# Cycle 03 Specification: Basic GUI (Read-Only)

## 1. Summary

This cycle marks the transition from backend logic to user interface. We will build the "Matome Canvas," a web-based GUI using the `Panel` library. The initial version will be read-only, focusing on the visualization of the DIKW hierarchy generated in Cycle 01.

Users will be able to start the application via `matome serve` (or similar), see the "Wisdom" (L1) node at the top of the screen, and interactively drill down into "Knowledge" (L2) and "Information" (L3) nodes. This "Semantic Zooming" capability is the core value proposition of the UI. We will adopt the MVVM (Model-View-ViewModel) pattern to keep the UI code clean and separate from the business logic.

## 2. System Architecture

### File Structure (ASCII Tree)

```
matome/
├── src/
│   ├── matome/
│   │   ├── ui/
│   │   │   ├── __init__.py
│   │   │   ├── **view_model.py**   # [Create] InteractiveSession (ViewModel)
│   │   │   └── **canvas.py**       # [Create] MatomeCanvas (View)
│   │   └── cli.py              # [Modify] Add 'serve' command
```

### Key Components

1.  **InteractiveSession (ViewModel):**
    Located in `src/matome/ui/view_model.py`.
    -   Inherits from `param.Parameterized`.
    -   **State:**
        -   `root_node`: The top-level Wisdom node.
        -   `current_view_nodes`: List of nodes currently visible.
        -   `selected_node`: The node currently focused by the user.
        -   `breadcrumbs`: Path from root to current selection.
    -   **Actions:**
        -   `load_tree(root_id)`: Initializes the session.
        -   `select_node(node_id)`: Updates selection and view state.

2.  **MatomeCanvas (View):**
    Located in `src/matome/ui/canvas.py`.
    -   **Components:**
        -   `Header`: Displays title and breadcrumbs.
        -   `PyramidView`: The main visualization area. Using `pn.Column` and `pn.Card` or `pn.GridBox` to represent hierarchy.
        -   `DetailPanel`: Side panel showing details of the `selected_node`.

3.  **CLI Command:**
    -   `matome serve <db_path>`: Starts the Panel server.

## 3. Design Architecture

### MVVM Pattern Implementation

```python
import param
import panel as pn
from domain_models.manifest import SummaryNode

class InteractiveSession(param.Parameterized):
    selected_node = param.ClassSelector(class_=SummaryNode, allow_None=True)

    def __init__(self, engine):
        self.engine = engine
        super().__init__()

    def select_node(self, node_id: str):
        node = self.engine.get_node(node_id)
        self.selected_node = node
        # Logic to update breadcrumbs and visible children...

class MatomeCanvas:
    def __init__(self, session: InteractiveSession):
        self.session = session

    def view(self):
        # Bind the view to the ViewModel's parameters
        return pn.Row(
            self._render_tree(),
            self._render_details()
        )

    def _render_details(self):
        # Automatically updates when session.selected_node changes
        return pn.bind(self._node_detail_view, self.session.param.selected_node)
```

### UI Layout (Concept)
-   **Top:** Global Navigation (Breadcrumbs: "Wisdom > Knowledge: Structure > Information: Steps").
-   **Left (Main):** The Tree View. Root at top. Children arranged horizontally below parent.
-   **Right (Details):** Full text of the selected node. Metadata display.

## 4. Implementation Approach

1.  **Step 1: Setup Panel**
    -   Create `src/matome/ui/` directory.
    -   Ensure `panel` and `watchfiles` are installed (via pyproject.toml).

2.  **Step 2: Implement ViewModel (InteractiveSession)**
    -   Define the `param` class.
    -   Implement `load_tree` to fetch the Root Node from `DiskChunkStore`.
    -   Implement `get_children` helper.

3.  **Step 3: Implement View (MatomeCanvas)**
    -   Create a basic layout with `pn.template.MaterialTemplate`.
    -   Implement `_render_node(node)` which returns a `pn.Card` or `pn.Button`.
    -   Wire up click events: `on_click=lambda e: session.select_node(node.id)`.

4.  **Step 4: CLI Command**
    -   Add `serve` command to `cli.py`.
    -   It should initialize `DiskChunkStore`, create `InteractiveSession`, create `MatomeCanvas`, and call `pn.serve(canvas.view)`.

## 5. Test Strategy

### Unit Testing Approach (Min 300 words)
-   **ViewModel Logic:** We will test `InteractiveSession` without the UI.
    -   Call `session.select_node(child_id)`. Assert `session.selected_node.id == child_id`.
    -   Assert `breadcrumbs` updates correctly.
-   **Mock Engine:** Pass a mock engine to the session to avoid DB dependency in unit tests.

### Integration Testing Approach (Min 300 words)
-   **UI Launch:** We will write a test that attempts to launch the server on a random port and verifies it responds to HTTP requests (basic "is it alive" check).
-   **Click Simulation:** Using `playwright` or Panel's testing capabilities (if applicable), simulate a click on a node and verify the detail pane updates. Since this is complex, manual verification via UAT is emphasized for this cycle.
