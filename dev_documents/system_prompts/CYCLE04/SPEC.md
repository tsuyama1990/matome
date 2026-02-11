# Cycle 04: GUI Foundation (MVVM) - Specification

## 1. Summary

This cycle marks the beginning of the visual interface. We will implement the foundation of the Matome Canvas using the **Panel** library. The goal is to visualize the DIKW tree stored in `chunks.db` and allow basic navigation (Semantic Zooming). To ensure maintainability and separation of concerns, we will strictly adhere to the **Model-View-ViewModel (MVVM)** pattern. The `InteractiveSession` (ViewModel) will mediate between the `InteractiveRaptorEngine` (Model) and the Panel widgets (View).

## 2. System Architecture

We introduce the `interface` package.

```ascii
src/
├── matome/
│   ├── interface/
│   │   ├── **app.py**         # NEW: Application Entry Point
│   │   ├── **viewmodel.py**   # NEW: InteractiveSession (ViewModel)
│   │   └── **components.py**  # NEW: UI Components (Tree, Detail)
│   └── ...
```

**Key Changes:**
1.  **`src/matome/interface/viewmodel.py`**:
    -   `InteractiveSession(param.Parameterized)`: Holds the state (`selected_node`, `tree_root`, etc.) and exposes actions (`select_node`, `load_tree`).
2.  **`src/matome/interface/components.py`**:
    -   `TreeNavigator`: A component to visualize the hierarchy (e.g., using `pn.Column` recursively or a dedicated tree widget).
    -   `NodeDetailView`: Displays the content of the `selected_node`.
3.  **`src/matome/interface/app.py`**:
    -   Wiring: Instantiates the Engine, the Session, and the View components, then serves the app.

## 3. Design Architecture

### 3.1. MVVM Pattern

**Model:**
-   `SummaryNode` (Data)
-   `InteractiveRaptorEngine` (Service)

**ViewModel (`InteractiveSession`):**
```python
import param
from matome.domain_models.manifest import SummaryNode

class InteractiveSession(param.Parameterized):
    root_node = param.ClassSelector(class_=SummaryNode)
    selected_node = param.ClassSelector(class_=SummaryNode)
    is_loading = param.Boolean(default=False)

    def __init__(self, engine, **params):
        super().__init__(**params)
        self.engine = engine

    def load_tree(self):
        self.is_loading = True
        # Fetch root from engine
        self.root_node = self.engine.get_root()
        self.selected_node = self.root_node
        self.is_loading = False

    def select_node(self, node_id: str):
        self.selected_node = self.engine.get_node(node_id)
```

**View:**
-   **Reactive:** Components bind to `session.selected_node` or `session.root_node`. When these parameters change, the view updates automatically.
-   **No Logic:** The View should not contain business logic (e.g., fetching data directly). It only calls methods on the Session.

### 3.2. Tree Visualization

For the initial version, we can use a simple recursive layout or a `pn.widgets.Tree` (if available/suitable) or `Collapsible` cards.
Given the DIKW nature:
-   **Root (Wisdom):** Always visible at top.
-   **Children (Knowledge):** Expandable section below.
-   **Grandchildren (Action):** Further nested.

## 4. Implementation Approach

### Step 1: Create InteractiveSession
1.  In `src/matome/interface/viewmodel.py`, define the class.
2.  Implement `load_tree` and `select_node` logic.

### Step 2: Implement Components
1.  In `src/matome/interface/components.py`.
2.  `NodeDetailView`: A markdown pane (`pn.pane.Markdown`) bound to `session.selected_node.text`.
    ```python
    def detail_view(session):
        return pn.pane.Markdown(object=session.param.selected_node.text)
    ```
3.  `TreeNavigator`: A component that iterates through `session.root_node` children and renders buttons/links. Clicking them calls `session.select_node`.

### Step 3: Application Wiring
1.  In `src/matome/interface/app.py`.
2.  Initialize `DiskChunkStore` and `InteractiveRaptorEngine`.
3.  Initialize `InteractiveSession(engine=engine)`.
4.  Layout the template: `pn.template.MaterialTemplate` with Sidebar (Tree) and Main (Detail).
5.  `pn.serve(app)` or `app.servable()`.

## 5. Test Strategy

### 5.1. Unit Testing (ViewModel)
-   **State Changes:**
    -   Instantiate `InteractiveSession` with a mock engine.
    -   Call `load_tree()`. Verify `root_node` is populated and `is_loading` toggles True -> False.
    -   Call `select_node("123")`. Verify `selected_node.id` becomes "123".

### 5.2. Component Testing
-   **Rendering:**
    -   Instantiate a component with a dummy session.
    -   Check if the output object (Panel object) contains the expected text.
    -   (Note: Full GUI testing is hard; we rely on unit tests for logic and manual UAT for visuals).

### 5.3. Integration (Launch Test)
-   **Smoke Test:**
    -   Run `python -m matome.interface.app`.
    -   Ensure the server starts without crashing (no `ImportError`, etc.).
