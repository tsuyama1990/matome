# Cycle 05: Semantic Zooming & Interactive Refinement - Specification

## 1. Summary

Cycle 05 delivers the "killer features" of Matome 2.0: **Semantic Zooming** and **Interactive Refinement**. This cycle transforms the basic GUI from Cycle 04 into a powerful knowledge installation tool.

**Semantic Zooming** allows users to traverse the DIKW hierarchy intuitively. Instead of a flat list, the interface will visually represent the pyramid structure—starting with the single "Wisdom" node and expanding into "Knowledge" branches and "Action" leaves upon interaction.

**Interactive Refinement** closes the loop between the user and the AI. Users can select any node and provide natural language instructions (e.g., "Make this simpler," "Add an example") via a chat interface. The system will process this request using the `InteractiveRaptorEngine` and update the database and UI in real-time, creating a personalized "Knowledge Base."

## 2. System Architecture

### File Structure

```ascii
src/
├── matome/
│   ├── gui/
│   │   ├── **components/**     # [MODIFIED] Add Zoom and Chat components
│   │   │   ├── **zoom_view.py**
│   │   │   └── **chat_view.py**
│   │   └── app.py              # [MODIFIED] Integrate new components
```

## 3. Design Architecture

### 3.1. Zoom View (`src/matome/gui/components/zoom_view.py`)

This component visualizes the hierarchical nature of the data. We will use a nested layout approach (e.g., `pn.Card` or custom HTML/CSS) to represent parent-child relationships.

**Logic:**
-   **Initial State:** Show only Root (Wisdom).
-   **Interaction:** Clicking Root expands its children (Knowledge).
-   **Visuals:** Different colors/styles for each DIKW level (Gold for Wisdom, Blue for Knowledge, Green for Action).

```python
class ZoomView(pn.viewable.Viewer):
    def __init__(self, session: InteractiveSession, **params):
        # ... bind to session.root_node ...
        pass

    def render_node(self, node):
        # Recursive rendering or dynamic loading on click
        card = pn.Card(..., title=node.text[:50])
        # On click -> session.select_node(node.id)
        return card
```

### 3.2. Chat View (`src/matome/gui/components/chat_view.py`)

This component handles the "Refinement" use case. It uses Panel's built-in `ChatInterface` or a custom text input + history display.

**Logic:**
-   **Context:** Aware of `session.selected_node`.
-   **Input:** User types instruction.
-   **Action:** Calls `session.refine_node(instruction)`.
-   **Feedback:** Shows "Thinking..." spinner, then updates the node text in the ZoomView.

```python
class RefinementChat(pn.viewable.Viewer):
    def __init__(self, session: InteractiveSession):
        self.chat_feed = pn.WidgetBox(...)
        self.input_box = pn.widgets.TextInput(placeholder="Refine this node...")

    def send_refinement(self, event):
        instruction = self.input_box.value
        self.session.refine_node(instruction)
        # update UI
```

## 4. Implementation Approach

### Step 1: Implement ZoomView
1.  Create `src/matome/gui/components/zoom_view.py`.
2.  Use `pn.Column` and `pn.Row` to build a simple tree layout.
3.  Bind click events to `session.select_node`.

### Step 2: Implement ChatView
1.  Create `src/matome/gui/components/chat_view.py`.
2.  Add a `TextInput` and `Button`.
3.  Bind the button click to a method that triggers `session.refine_selected_node(instruction)`.

### Step 3: Update InteractiveSession
1.  Add `refine_selected_node(instruction)` method.
2.  This method should call `engine.refine_node`, then update `self.selected_node` to trigger a UI refresh.

### Step 4: Integrate into App
1.  Update `matome/gui/app.py` to place `ZoomView` in the main area and `RefinementChat` in a sidebar or bottom panel.

## 5. Test Strategy

### Unit Testing
*   **`tests/unit/test_view_components.py`**:
    *   (Requires careful mocking of Panel, or testing logic separation).
    *   Test that `RefinementChat` calls the correct session method when input is submitted.

### User Acceptance Testing (Manual)
*   **Drill-Down Test:** Open app. Click Wisdom. Verify 3-5 Knowledge nodes appear. Click Knowledge. Verify Action nodes appear.
*   **Refinement Test:** Select an Action node. Type "Translate to Japanese". Verify the text changes to Japanese within a few seconds.
