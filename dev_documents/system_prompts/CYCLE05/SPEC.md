# Cycle 05 Specification: Semantic Zooming & Final Polish

## 1. Summary

Cycle 05 is the final implementation phase where the system becomes truly "Interactive." While Cycle 04 established the UI skeleton, Cycle 05 breathes life into it by implementing the two core user stories: **Semantic Zooming** (Navigation) and **Knowledge Refinement** (Editing).

We will enable users to "drill down" from Wisdom to Data by clicking on nodes, revealing the hierarchical structure dynamically. Simultaneously, we will implement the Chat Interface, allowing users to select any node and issue natural language commands (e.g., "Simplify this explanation") to rewrite the content in real-time. Finally, we will add source traceability, ensuring that every piece of advice can be traced back to the original text chunks.

This cycle culminates in the Final User Acceptance Test (UAT), verifying that the tool effectively serves as a "Knowledge Installation" platform.

## 2. System Architecture

### 2.1. File Structure

```ascii
matome/
├── src/
│   ├── matome/
│   │   ├── interface/
│   │   │   ├── session.py          # MODIFY: Add navigation and refinement logic
│   │   │   └── components/
│   │   │       ├── **chat.py**     # CREATE: The Refinement Chat UI
│   │   │       └── **canvas.py**   # MODIFY: Add click handlers and drill-down views
├── tests/
│   └── e2e/
│       └── **test_full_workflow.py** # CREATE: End-to-End verification
└── pyproject.toml
```

### 2.2. Component Details

#### `src/matome/interface/components/chat.py` (New)
A Panel component (`pn.ChatFeed` or custom column) that:
-   Displays the conversation history for the *selected node*.
-   Provides an input box for user instructions.
-   Triggers `session.submit_refinement` on send.

#### `src/matome/interface/components/canvas.py` (Modification)
-   **Click Handlers**: Update node cards to be clickable (using `pn.bind` or button wrappers). Clicking a card triggers `session.select_node`.
-   **Drill-Down Logic**: If a node is expanded, display its children below it (or in a separate "Next Level" column, depending on layout choice).

#### `src/matome/interface/session.py` (Modification)
-   **`expand_node(node_id)`**: Fetches children of the node from the engine and adds them to the view state.
-   **`submit_refinement(instruction)`**:
    1.  Sets `is_processing = True`.
    2.  Calls `engine.refine_node(selected_node.id, instruction)`.
    3.  Updates `selected_node` with the result.
    4.  Sets `is_processing = False`.

## 3. Design Architecture

### 3.1. Navigation Flow (Semantic Zooming)

The navigation follows a "Progressive Disclosure" pattern.
1.  **Initial State**: Only Root (Wisdom) is visible.
2.  **User Action**: Click Root.
3.  **System Response**: Fetch Level 1 children (Knowledge). Display them in a row/grid below the Root.
4.  **User Action**: Click a Knowledge Node.
5.  **System Response**: Fetch Level 0 children (Action). Display them below the Knowledge node.

To manage screen real estate, we might adopt a "Focus" strategy: clicking a node centers it and shows its direct children, potentially hiding siblings of the parent.

### 3.2. Refinement Flow (Chat)

1.  **Selection**: User clicks a node. The "Chat Panel" on the right updates to show "Editing: [Node Title]".
2.  **Input**: User types "Make this more concise".
3.  **Process**: The system locks the UI (`is_loading`), sends the request to the backend.
4.  **Update**: The backend updates the DB. The frontend receives the new node object. The Node Card in the center canvas updates immediately to reflect the new text. The Chat Panel shows a "Done" message.

### 3.3. Traceability

For Leaf Nodes (Action/Data), the "Detail View" must include a "Show Source" button.
-   **Logic**: `engine.get_children(leaf_node_id)` returns the original `Chunk` objects.
-   **Display**: A modal or expanding section showing the raw text from the source document.

## 4. Implementation Approach

### Step 1: Implement `src/matome/interface/components/chat.py`
1.  Create a `RefinementChat` class/function.
2.  Use `pn.widgets.ChatBox` or `pn.Column` + `pn.widgets.TextInput`.
3.  Bind the "Send" action to a callback that invokes `session.submit_refinement`.

### Step 2: Update `src/matome/interface/session.py`
1.  Implement `submit_refinement`. Ensure it handles exceptions (e.g., API errors) and updates `is_processing`.
2.  Implement `expand_node`. Manage a `expanded_nodes` set or list to track what should be visible.

### Step 3: Upgrade `src/matome/interface/components/canvas.py`
1.  Modify `render_node_card` to include a click event.
2.  Implement the recursive or iterative layout logic to render the tree based on `session.expanded_nodes`.

### Step 4: Traceability
1.  Add logic in `session.py` to fetch chunks if the selected node is a leaf.
2.  Display these chunks in `canvas.py` or the side panel.

## 5. Test Strategy

### 5.1. End-to-End (E2E) Testing (Min 300 words)
Because this cycle involves complex user interactions, automated unit tests are insufficient. We rely on a rigorous manual UAT plan (defined in `FINAL_UAT.md`) and potentially scripted browser tests if time permits.

**Manual Verification Walkthrough**:
1.  **Zoom**: Open app. Click Root. Verify 3-5 children appear. Click a child. Verify grandchildren appear.
2.  **Refine**: Select a child. Type "Add emoji". Wait. Verify text now has emoji. Reload page. Verify emoji persists.
3.  **Source**: Select a leaf. Click "Show Source". Verify the original text displayed matches the context of the summary.

**`tests/e2e/test_full_workflow.py`** (Simulated):
-   Mock the `InteractiveRaptorEngine` entirely.
-   Script a sequence of `session` method calls:
    -   `session.load_tree()`
    -   `session.select_node(root.id)`
    -   `session.expand_node(root.id)` -> Assert children are loaded.
    -   `session.submit_refinement("test")` -> Assert node text updates.
-   This ensures the *logic* of the UI holds together, even if the pixels aren't verified.
