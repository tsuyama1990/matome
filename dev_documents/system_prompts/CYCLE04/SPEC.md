# Cycle 04 Specification: GUI Foundation (MVVM)

## 1. Summary

Cycle 04 focuses on establishing the graphical user interface (GUI) using the Panel library. To ensure the UI code remains clean and testable, we will strictly adhere to the Model-View-ViewModel (MVVM) pattern. The `InteractiveSession` class will serve as the ViewModel, mediating between the `InteractiveRaptorEngine` (Model) and the `MatomeCanvas` (View). This cycle delivers the foundational layout and state management required for the full Semantic Zooming experience in Cycle 05. The primary goal is to provide a responsive interface for visualizing the Knowledge Graph.

## 2. System Architecture

We will implement the UI components and integrate them into the CLI.

```ascii
src/
├── matome/
│   ├── ui/
│   │   ├── session.py       # [NEW] InteractiveSession (ViewModel)
│   │   └── canvas.py        # [NEW] MatomeCanvas (View)
│   └── cli.py               # [MODIFIED] Add `serve` command
```

**New Classes:**
- **`InteractiveSession`**: A state container that exposes `param.Parameterized` properties. It handles business logic for UI actions (e.g., selecting a node, submitting refinement).
- **`MatomeCanvas`**: A declarative UI definition using `panel`. It binds directly to `InteractiveSession` properties, updating automatically when the state changes.

**Modified Components:**
- **`cli.py`**: Added `serve` command to launch the `panel serve` process.

## 3. Design Architecture

### 3.1. InteractiveSession (ViewModel)

This class holds the runtime state of the UI and exposes methods for user actions. It does *not* contain any layout code.

**State Variables (param):**
- `selected_node`: `param.ClassSelector(class_=SummaryNode, allow_None=True)`: The currently active node.
- `current_level`: `param.Selector(objects=list(DIKWLevel), default=DIKWLevel.WISDOM)`: The abstraction level being viewed.
- `is_refining`: `param.Boolean(default=False)`: Flag indicating if a refinement operation is in progress (used to show loading spinner).
- `refinement_instruction`: `param.String(default="")`: The text entered by the user.
- `status_message`: `param.String(default="Ready")`: User feedback.

**Actions:**
- `select_node(node_id: str)`: Fetches the node from the engine and updates `selected_node`.
- `submit_refinement()`: Calls `engine.refine_node` with the current instruction, updates the node, resets the instruction, and updates `status_message`.

**`src/matome/ui/session.py` Example:**

```python
import param
from matome.engines.interactive import InteractiveRaptorEngine

class InteractiveSession(param.Parameterized):
    selected_node = param.ClassSelector(class_=SummaryNode, allow_None=True)
    # ... other params ...

    def __init__(self, engine: InteractiveRaptorEngine, **params):
        super().__init__(**params)
        self.engine = engine

    def select_node(self, node_id: str):
        self.selected_node = self.engine.get_node(node_id)
        self.status_message = f"Selected node {node_id}"
```

### 3.2. MatomeCanvas (View)

This module defines the visual layout. It observes the `InteractiveSession` and updates reactively.

**Layout Structure (Panel):**
- **Header:** App Title and Global Status.
- **Main Area (Split):**
    - **Left (Navigation):** Tree or List view of nodes filtered by `current_level`. Uses `pn.widgets.Select` or custom HTML list.
    - **Right (Detail):** Content of `selected_node`. Includes text area, metadata display, and refinement controls.
- **Footer:** Status bar.

**Reactive Bindings:**
- Use `pn.bind` or `@param.depends` to link UI components to session properties.
- Example: The detail pane updates automatically when `session.selected_node` changes.
- Example: The "Submit" button is disabled if `session.is_refining` is True.

## 4. Implementation Approach

This cycle focuses on getting the "plumbing" right before adding advanced features.

### Step 1: Implement ViewModel
Create `src/matome/ui/session.py`. Ensure it accepts an `InteractiveRaptorEngine` instance in `__init__`.
- Implement basic state management for selection and level filtering.

### Step 2: Implement View Components
Create `src/matome/ui/canvas.py`. Build small components first (e.g., `NodeDetailView`, `LevelSelector`).
- Use `pn.Column` and `pn.Row` for layout.
- Ensure the UI is responsive.

### Step 3: CLI Integration
Update `src/matome/cli.py` to add a `serve` command. This command should:
1. Initialize `DiskChunkStore` and `InteractiveRaptorEngine`.
2. Create an `InteractiveSession`.
3. Launch `pn.serve(MatomeCanvas(session).layout)`.

## 5. Test Strategy

Testing focuses on the logic within the ViewModel, as testing the UI directly (pixel-perfect) is brittle.

### 5.1. Unit Testing (ViewModel)
**File:** `tests/ui/test_session.py`
- **Test Case 1: Selection Logic**
    - **Setup:** Mock engine.
    - **Action:** Call `session.select_node("id")`.
    - **Assertion:** `session.selected_node` is updated to the mock node.
- **Test Case 2: Refinement State**
    - **Setup:** Mock engine.refine_node (slow).
    - **Action:** Call `session.submit_refinement()`.
    - **Assertion:** Verify `is_refining` toggles True then False. Verify `refinement_instruction` is cleared.

### 5.2. Integration Testing (View Launch)
**File:** `tests/ui/test_canvas_launch.py`
- **Test Case 1: Layout Construction**
    - **Setup:** Create session and canvas.
    - **Action:** Access `canvas.layout`.
    - **Assertion:** Returns a valid Panel object. No exceptions raised.
- **Test Case 2: Server Start**
    - **Action:** Use `subprocess` to run `matome serve` (briefly).
    - **Assertion:** Process starts and binds to port (check output logs).
