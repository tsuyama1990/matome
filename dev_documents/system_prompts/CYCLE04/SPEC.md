# Cycle 04 Specification: GUI Foundation (MVVM)

## 1. Summary

Cycle 04 initiates the development of the graphical user interface, **Matome Canvas**. We will adopt the **Model-View-ViewModel (MVVM)** pattern using the **Panel** framework to ensure a clean separation between the UI layout (View) and the application state (ViewModel). This cycle focuses on setting up the project structure for the GUI, implementing the core `InteractiveSession` logic, and creating the initial visual components to display the root (Wisdom) node of the knowledge tree.

## 2. System Architecture

```ascii
src/matome/
├── canvas/
│   ├── **__init__.py**
│   ├── **app.py**              # New: Main entry point for the Panel app (View)
│   ├── **session.py**          # New: InteractiveSession (ViewModel)
│   └── **components.py**       # New: Reusable UI components (WisdomCard)
├── **cli.py**                  # Modified: Add "canvas" command to launch the GUI
└── ...
```

### Key Changes
1.  **Dependencies**: Add `panel`, `param`, and `watchfiles` to `pyproject.toml` (runtime dependencies).
2.  **`src/matome/canvas/session.py`**: The `InteractiveSession` class, inheriting from `param.Parameterized`.
3.  **`src/matome/canvas/components.py`**: UI widgets like `WisdomCard`.
4.  **`src/matome/canvas/app.py`**: The main layout that assembles components.

## 3. Design Architecture

### 3.1. MVVM Pattern with Panel

**Model**: `SummaryNode` (Data) & `InteractiveRaptorEngine` (Controller).
**ViewModel**: `InteractiveSession`.
**View**: `MatomeApp` & Components.

### 3.2. Class Definitions

**`InteractiveSession` (ViewModel)**
```python
import param

class InteractiveSession(param.Parameterized):
    # State Variables
    selected_node = param.ClassSelector(class_=SummaryNode, allow_None=True)
    current_root = param.ClassSelector(class_=SummaryNode, allow_None=True)

    # Dependencies
    engine: InteractiveRaptorEngine

    def load_tree(self):
        """Loads the root node from the engine."""
        ...

    def select_node(self, node_id: str):
        """Updates selected_node."""
        ...
```

**`MatomeApp` (View)**
```python
import panel as pn

class MatomeApp:
    def __init__(self, session: InteractiveSession):
        self.session = session

    def view(self):
        """Returns the Panel layout."""
        return pn.Column(
            "# Matome Canvas",
            WisdomCard(self.session.current_root),
            ...
        )
```

## 4. Implementation Approach

### Step 1: Install Dependencies
Add `panel>=1.0.0`, `param>=2.0.0`, `watchfiles` to `pyproject.toml`.

### Step 2: Implement InteractiveSession
Create `src/matome/canvas/session.py`.
*   Define the class with `param`.
*   Initialize it with an instance of `InteractiveRaptorEngine`.
*   Implement `load_initial_state()` to fetch the Wisdom node (L1).

### Step 3: Create UI Components
Create `src/matome/canvas/components.py`.
*   Implement `WisdomCard(node: SummaryNode)`. It should display the summary text in a large font and the metadata.
*   Make it reactive: if the node changes, the card updates.

### Step 4: Assemble the App
Create `src/matome/canvas/app.py`.
*   Instantiate `InteractiveSession`.
*   Create a `main` function that serves the app using `pn.serve`.

### Step 5: CLI Integration
Update `src/matome/cli.py`.
*   Add a `canvas` command (e.g., `matome canvas`).
*   This command initializes the engine and launches the Panel server.

## 5. Test Strategy

### 5.1. Unit Testing
*   **`tests/test_session.py`**:
    *   Test `InteractiveSession` state transitions.
    *   Mock the engine. Call `session.select_node("1")` and verify `session.selected_node` updates.
*   **`tests/test_components.py`**:
    *   (Optional) Test component rendering if possible without a browser (using `panel`'s test utilities).

### 5.2. Smoke Testing
*   **Manual Launch**: Run `matome canvas`.
*   **Verification**:
    *   Server starts on `localhost:5006`.
    *   Browser opens.
    *   The "Wisdom" node from `chunks.db` is displayed.
