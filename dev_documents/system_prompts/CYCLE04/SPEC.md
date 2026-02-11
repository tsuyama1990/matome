# Cycle 04: GUI Foundation (MVVM Pattern)

## 1. Summary

This cycle establishes the graphical user interface (GUI) using the **Panel** library. To ensure scalability and separation of concerns, we adopt the **MVVM (Model-View-ViewModel)** architectural pattern.

The goal is to render the initial state of the knowledge tree (specifically the Root/Wisdom node) and set up the reactive infrastructure (`param` based signals) that will drive future interactivity.

## 2. System Architecture

We introduce the `src/matome/ui` package.

```ascii
src/matome/
├── ui/
│   ├── **session.py**          # [NEW] ViewModel (InteractiveSession)
│   └── **canvas.py**           # [NEW] View (MatomeCanvas)
└── **cli.py**                  # [MOD] Add `ui` command to launch server
```

### Files to Modify/Create

1.  **`src/matome/ui/session.py`**
    *   **Action**: Create `InteractiveSession` class inheriting from `param.Parameterized`. This is the ViewModel.
2.  **`src/matome/ui/canvas.py`**
    *   **Action**: Create `MatomeCanvas` class. This is the View, responsible for layout (Panel components).
3.  **`src/matome/cli.py`**
    *   **Action**: Add a `ui` command (e.g., `matome ui <db_path>`) that starts the Panel server.

## 3. Design Architecture

### 3.1. Model-View-ViewModel (MVVM)

*   **Model**: The `SummaryNode` objects and `DiskChunkStore` (the data source).
*   **ViewModel (`InteractiveSession`)**:
    *   Manages the state of the application.
    *   Exposes reactive parameters: `current_node` (SummaryNode), `is_loading` (bool), `status_message` (str).
    *   Contains business logic methods: `load_root()`, `select_node(node_id)`.
*   **View (`MatomeCanvas`)**:
    *   Declarative UI definition using `panel`.
    *   Binds to ViewModel parameters (e.g., `value=session.param.current_node`).
    *   **No business logic** inside the View.

### 3.2. Panel Implementation Details

*   **Layout**: A simple 2-column layout (or master-detail).
    *   **Sidebar (Left)**: Navigation or Stats.
    *   **Main (Center)**: The current node visualization (Card view).
*   **Reactivity**: Use `pn.bind` or `param.watch` to update the view when `session.current_node` changes.

## 4. Implementation Approach

1.  **ViewModel**: Implement `InteractiveSession`. It should take `DiskChunkStore` as a dependency. Implement `load_root()` to fetch the L1 Wisdom node.
2.  **View**: Implement `MatomeCanvas`. Create a method `view()` that returns a `pn.template.MaterialTemplate` or similar.
    *   Render the `current_node` as a Markdown pane.
3.  **CLI**: Use `panel.serve` to launch the application.
    *   Command: `uv run matome ui chunks.db`

## 5. Test Strategy

### 5.1. Unit Testing (ViewModel)
*   **State Logic**: Test `InteractiveSession`.
    *   Call `session.load_root()`.
    *   Assert `session.current_node` is not None.
    *   Assert `session.current_node.dikw_level == DIKWLevel.WISDOM`.

### 5.2. Integration Testing (Launch)
*   **Server Start**: Verify that `panel serve` starts without errors.
*   **UI Rendering**: Since Panel is web-based, we can use `playwright` (if available) or manual verification.
    *   **Manual**: Open `http://localhost:5006`. Verify the Wisdom node from `test_data` is displayed.
