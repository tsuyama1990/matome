# Cycle 04 Specification: GUI Foundation (MVVM)

## 1. Summary

Cycle 04 represents the visible transformation of Matome. This cycle introduces the **Graphical User Interface (GUI)** using the `Panel` framework, adhering to the **Model-View-ViewModel (MVVM)** pattern. The goal is to create the foundational structure of the "Matome Canvas" application, enabling users to launch a web interface, load a processed database, and view the high-level "Wisdom" (Root Node) of a document.

While previous cycles focused on backend logic (DIKW generation, interactive engine), this cycle bridges the gap to the user. We will implement:
1.  **ViewModel (`InteractiveSession`):** A class that manages the application state (e.g., currently loaded tree, selected node, expanded branches) using the `param` library for reactive programming.
2.  **View (`MatomeCanvas`):** A Panel-based UI component that observes the ViewModel and renders the tree structure.
3.  **Application Entry Point:** A script to launch the Panel server.

Crucially, this cycle does not yet include the complex drill-down or refinement interactions (reserved for Cycle 05). The focus is on **architecture and initial rendering**. We want to ensure the MVVM pattern is correctly implemented so that future UI complexity remains manageable. The deliverable is a running web app that displays the Wisdom node.

## 2. System Architecture

The architecture adds the `ui/` package to the source tree.

### 2.1. Updated File Structure

```ascii
src/matome/
├── engines/
│   ├── interactive.py
│   └── ...
├── ui/
│   ├── **__init__.py**
│   ├── **app.py**          # Entry point (panel serve)
│   ├── **view_model.py**   # InteractiveSession
│   └── **components.py**   # UI Widgets (NodeCard, etc.)
└── ...
```

### 2.2. Component Interaction (MVVM)

```mermaid
graph TD
    User --> View[MatomeCanvas (View)]
    View -->|Observes| ViewModel[InteractiveSession (ViewModel)]
    ViewModel -->|Calls| IRE[InteractiveRaptorEngine (Model)]
    IRE -->|Reads| DB[DiskChunkStore]

    subgraph "Reactive Flow"
        IRE -- Returns Data --> ViewModel
        ViewModel -- Updates Params --> View
        View -- Re-renders --> User
    end
```

## 3. Design Architecture

### 3.1. ViewModel (`src/matome/ui/view_model.py`)

The `InteractiveSession` class holds the state.

```python
import param
from matome.engines.interactive import InteractiveRaptorEngine
from domain_models.manifest import SummaryNode

class InteractiveSession(param.Parameterized):
    """
    ViewModel for the Matome Canvas.
    Manages the state of the interactive session.
    """
    # Dependencies
    engine: InteractiveRaptorEngine = param.ClassSelector(class_=InteractiveRaptorEngine)

    # State
    root_node: SummaryNode | None = param.ClassSelector(class_=SummaryNode, default=None)
    selected_node_id: str | None = param.String(default=None)

    # Actions
    def load_tree(self, db_path: str):
        """Initialize the engine and load the root node."""
        # ... logic to init store and engine ...
        # self.engine = ...
        # root = self.engine.get_root()
        # self.root_node = root

    def select_node(self, node_id: str):
        """Update selection state."""
        self.selected_node_id = node_id
```

### 3.2. View (`src/matome/ui/components.py` & `app.py`)

We use Panel's reactive functions (`@pn.depends`) or `pn.bind` to link UI elements to ViewModel parameters.

```python
# src/matome/ui/components.py
import panel as pn
from matome.ui.view_model import InteractiveSession

class MatomeCanvas(pn.viewable.Viewer):
    def __init__(self, session: InteractiveSession):
        self.session = session
        super().__init__()

    def __panel__(self):
        # Layout definition
        return pn.Column(
            self._render_header,
            self._render_root_card
        )

    @pn.depends("session.root_node")
    def _render_root_card(self):
        if not self.session.root_node:
            return pn.pane.Markdown("### No document loaded.")

        node = self.session.root_node
        return pn.Card(
            pn.pane.Markdown(node.text),
            title="Wisdom (Root)",
            header_background="#f0f0f0",
            collapsed=False
        )
```

## 4. Implementation Approach

### Step 1: Create `src/matome/ui/view_model.py`
*   Implement `InteractiveSession`.
*   Add logic to load `DiskChunkStore` given a path.
*   Add logic to fetch the root node via `InteractiveRaptorEngine`.

### Step 2: Create `src/matome/ui/components.py`
*   Implement `MatomeCanvas`.
*   Create a reusable `NodeCard` component (Panel Card or Column) that takes a `SummaryNode` and renders it with style.
*   Use `dikw_level` metadata to style the card (e.g., Gold border for Wisdom).

### Step 3: Create `src/matome/ui/app.py`
*   This is the main script.
*   It should use `typer` or `argparse` to accept a `db_path`.
*   It initializes `InteractiveSession`.
*   It calls `session.load_tree(path)`.
*   It serves the `MatomeCanvas(session)` using `pn.serve`.

## 5. Test Strategy

### 5.1. Unit Testing Approach (Min 300 words)
*   **ViewModel Logic:**
    *   Test `InteractiveSession.load_tree`: Mock the engine. Verify that `root_node` param is updated after loading.
    *   Test `InteractiveSession.select_node`: Verify `selected_node_id` changes.
*   **Component Rendering:**
    *   Instantiate `MatomeCanvas` with a mock session.
    *   Set `session.root_node` to a dummy node.
    *   Check if `_render_root_card` returns a Panel object containing the dummy text. (Panel objects can be inspected via `.object` or `str()`).

### 5.2. Integration Testing Approach (Min 300 words)
*   **Launch Test:**
    *   Script that runs `panel serve src/matome/ui/app.py` in a subprocess.
    *   Wait for port 5006 (default).
    *   Assert process is running.
    *   Kill process.
*   **Visual Verification (Manual):**
    *   Run the app pointing to a real `chunks.db`.
    *   Open browser at localhost.
    *   Verify the Wisdom node is displayed clearly.
    *   Verify styling (DIKW levels visual cues).

This cycle provides the "Hello World" of the GUI.
