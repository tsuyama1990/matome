# Cycle 05: Semantic Zooming & Polish

## 1. Summary

In this final cycle, we will complete the **Matome Canvas** by implementing the core interactive features: **Pyramid Navigation (Semantic Zooming)** and **Chat-Based Refinement**.

The goal is to deliver the full user experience described in the "Aha!" moment scenario. Users should be able to click on a high-level "Wisdom" node to reveal its underlying "Knowledge," and then drill down further to "Information." Additionally, they should be able to select any node and "talk" to it, refining the summary using natural language.

## 2. System Architecture

We will expand the UI module with reusable components and full layout logic.

### File Structure
```
src/
├── matome/
│   ├── ui/
│   │   ├── **components.py** # Create: Reusable UI widgets (NodeCard, ChatBox)
│   │   └── **canvas.py**     # Modify: Full layout implementation
```

## 3. Design Architecture

### 3.1. Navigation Logic (Semantic Zooming)

The navigation follows a "Drill-Down" pattern.
- **Breadcrumbs**: Tracks the path from Root to Current Node.
- **Children View**: Displays the children of the current node as clickable cards. Clicking a child updates `current_node`.
- **Source View**: If the current node is a leaf (L3 Information), display the original text chunks (L4 Data).

### 3.2. Chat Interface (Refinement)

We will use `panel.chat` or a simple `TextInput` + `Button` combo.
- **Input**: User types instruction (e.g., "Make shorter").
- **Action**: Calls `session.refine_current_node(instruction)`.
- **Feedback**: Show a loading spinner, then update the node text in place.

### 3.3. UI Components (`src/matome/ui/components.py`)

To keep `canvas.py` clean, we extract widgets.
- `NodeCard`: Displays a summary node. Handles click events.
- `BreadcrumbParams`: Reactive breadcrumb list.
- `ChatArea`: Handles the chat interaction.

## 4. Implementation Approach

1.  **Enhance Session**:
    - Add `navigate_up()`: Go to parent.
    - Add `refine_current_node(instruction)`: Calls `engine.refine_node` and updates `current_node`.

2.  **Implement Navigation**:
    - In `canvas.py`, adding a "Children" section.
    - Iterate over `session.child_nodes` and create `NodeCard`s.
    - Bind click events to `session.load_node(child.id)`.

3.  **Implement Chat**:
    - Add a `pn.widgets.TextAreaInput` and `pn.widgets.Button` ("Refine").
    - On click, call `session.refine_current_node`.
    - Ensure the UI updates with the new text automatically (reactive binding).

4.  **Implement Source View**:
    - If `session.current_node` has no children (is leaf), fetch original chunks.
    - Display them in an `pn.Accordion` or similar.

5.  **Polish**:
    - Apply CSS for a clean, modern look.
    - Handle loading states gracefully.

## 5. Test Strategy

### End-to-End User Testing (Manual)
Since this cycle focuses on the GUI, manual verification is primary.
- **Navigation**:
    - Launch app.
    - Click Root -> Child -> Leaf.
    - Check Breadcrumbs update.
    - Click "Back" or Breadcrumb to go up.
- **Refinement**:
    - Select a node.
    - Type "Add an emoji".
    - Click Refine.
    - Verify text updates with an emoji.
- **Source Traceability**:
    - Go to a leaf node.
    - Verify original text chunks are visible.

### Automated Testing (UI Logic)
- **Callback Wiring**:
    - Instantiate `InteractiveSession`.
    - Mock `engine.refine_node`.
    - Call `session.refine_current_node("test")`.
    - Verify the mock was called with correct ID and instruction.
    - Verify `session.current_node` was updated with the return value.
