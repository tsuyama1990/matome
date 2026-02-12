# Cycle 05 Specification: Semantic Zooming & Final Polish

## 1. Summary

Cycle 05 delivers the full "Knowledge Installation" experience. We will expand the GUI to support **Semantic Zooming** (drill-down navigation) and **Interactive Refinement** (chat-based editing). This involves connecting the `InteractiveSession` logic developed in Cycle 04 to the `InteractiveRaptorEngine` methods implemented in Cycle 03, creating a cohesive user journey. Additionally, we will finalize the user documentation and ensure the system is production-ready.

## 2. System Architecture

```ascii
src/matome/
├── canvas/
│   ├── **components.py**       # Modified: Add DrillDownPanel, RefinementChat
│   ├── **app.py**              # Modified: Assemble full UI
│   └── **session.py**          # Modified: Connect refine_node and get_children
└── ...
```

### Key Changes
1.  **`src/matome/canvas/components.py`**:
    *   `DrillDownPanel`: Displays a list of children for the selected node.
    *   `RefinementChat`: A chat interface (input + message history) linked to the selected node.
    *   `SourcePanel` (Optional): Displays the original text (L4) if available.
2.  **`src/matome/canvas/session.py`**:
    *   `refine_current_node(instruction: str)`: Calls the engine's `refine_node`.
    *   `navigate_down(node: SummaryNode)`: Calls the engine's `get_children` and updates `current_children`.

## 3. Design Architecture

### 3.1. UI Layout (Panel)

The application will feature a split-pane or column-based layout.

*   **Top/Left:** The "Wisdom" or Parent View.
*   **Center/Right:** The "Drill-Down" or Children View.
*   **Bottom/Overlay:** The Refinement Interface.

### 3.2. Interaction Flow

1.  User clicks a node in the Drill-Down list.
2.  `session.select_node(clicked_node)` is triggered.
3.  The Refinement Chat context updates to this node.
4.  User types "Simplify this" in the chat.
5.  `session.refine_current_node("Simplify this")` is called.
6.  Engine processes, DB updates.
7.  Session receives updated node, updates `selected_node` param.
8.  UI re-renders with new text.

## 4. Implementation Approach

### Step 1: Implement Navigation Logic
Update `InteractiveSession` in `src/matome/canvas/session.py`.
*   Add `current_children = param.List(item_type=SummaryNode)`.
*   Implement `navigate_to(node)`: Fetch children from engine, update `current_children`.

### Step 2: Create Drill-Down Component
Update `src/matome/canvas/components.py`.
*   Create `DrillDownList`: A reactive component that renders `session.current_children`.
*   Each item should be clickable (triggering navigation or selection).

### Step 3: Implement Refinement Chat
Update `src/matome/canvas/components.py`.
*   Create `RefinementChat`:
    *   Input: `pn.widgets.TextInput`
    *   Button: "Refine"
    *   Action: Calls `session.refine_current_node(input.value)`.
    *   Display: Shows the `refinement_history` of the selected node.

### Step 4: Finalize App Layout
Update `src/matome/canvas/app.py`.
*   Arrange components logically (Wisdom at top, Children below, Chat on side or bottom).
*   Ensure the layout is responsive and clean.

### Step 5: Documentation & Polish
*   Update `README.md` with final screenshots (if possible) and instructions.
*   Create the tutorials defined in `FINAL_UAT.md`.

## 5. Test Strategy

### 5.1. Integration Testing (Manual)
*   **Navigation Test:** Load a tree. Click Wisdom. Verify Knowledge nodes appear. Click Knowledge. Verify Information nodes appear.
*   **Refinement Test:** Select an Information node. Type "Make it a bullet list". Click Refine. Wait. Verify the text changes to a bullet list. Verify the change persists after reload.

### 5.2. E2E Scenario
*   Execute the "Emin's Shikihou" scenario fully.
*   Validate the "Aha!" moment (Wisdom).
*   Validate the "Zoom-In" thrill (Navigation).
*   Validate the "Customization" (Refinement).
