# Cycle 04 Specification: Interactive Refinement (The "Write" Experience)

## 1. Summary

This cycle delivers the core "Knowledge Installation" promise: the ability to actively reshape the knowledge structure. Building upon the Read-Only GUI from Cycle 03 and the Interactive Engine from Cycle 02, we will now implement the "Write" capabilities in the Matome Canvas.

Users will be able to select any node in the DIKW tree and issue natural language instructions (e.g., "Simplify this," "Focus on the risks," "Translate to Japanese"). The system will process this request in real-time using the `InteractiveRaptorEngine` and update the visualization instantly. This transforms the tool from a passive reader into an active workspace for understanding.

## 2. System Architecture

### File Structure (ASCII Tree)

```
matome/
├── src/
│   ├── matome/
│   │   ├── ui/
│   │   │   ├── **canvas.py**       # [Modify] Add Chat Interface & Edit Controls
│   │   │   └── **view_model.py**   # [Modify] Add refinement actions & state management
```

### Key Components

1.  **Refinement Interface (UI):**
    Located in `src/matome/ui/canvas.py`.
    -   Adds a "Refinement Panel" next to the node details.
    -   Uses `pn.chat.ChatInterface` or a simple Text Input + Button combo.
    -   Displays a loading spinner during processing.

2.  **ViewModel Actions:**
    Located in `src/matome/ui/view_model.py`.
    -   `refine_current_node(instruction: str)`:
        1.  Sets `is_processing = True`.
        2.  Calls `self.engine.refine_node(self.selected_node.id, instruction)`.
        3.  Updates `self.selected_node` with the new result.
        4.  Triggers a view refresh.
        5.  Sets `is_processing = False`.

3.  **State Synchronization:**
    -   When `refine_node` returns, the `DiskChunkStore` is already updated.
    -   The ViewModel must ensure that the `SummaryNode` object in memory is replaced with the fresh one from the DB to reflect changes in the UI.

## 3. Design Architecture

### Interaction Flow

1.  **User Selects Node:** `selected_node` is updated. Detail view shows current text.
2.  **User Types Instruction:** "Make this a bulleted list."
3.  **User Clicks 'Refine':**
    -   UI locks input, shows spinner.
    -   ViewModel calls Engine.
    -   Engine calls Agent (LLM).
    -   Agent returns new text.
    -   Engine updates DB.
    -   Engine returns updated Node.
4.  **UI Updates:**
    -   Detail view shows new text.
    -   Metadata shows `is_user_edited: True`.
    -   Spinner disappears.

### Data Binding
We continue to use `param` for reactive updates.

```python
class InteractiveSession(param.Parameterized):
    # ... existing params ...
    is_processing = param.Boolean(default=False)

    def refine_current_node(self, instruction):
        if not self.selected_node: return

        self.is_processing = True
        try:
            # Call Cycle 02 Engine
            updated_node = self.engine.refine_node(self.selected_node.id, instruction)

            # Update local state to trigger UI refresh
            self.selected_node = updated_node
            # Force refresh of parent view if necessary (optional)
        finally:
            self.is_processing = False
```

## 4. Implementation Approach

1.  **Step 1: Update ViewModel**
    -   Add `refine_current_node` method to `InteractiveSession`.
    -   Add `is_processing` param.

2.  **Step 2: Update Canvas UI**
    -   In `_render_details`, add a `pn.Column` containing:
        -   The existing text display.
        -   A `pn.widgets.TextAreaInput` for instructions.
        -   A `pn.widgets.Button(name="Refine", button_type="primary")`.
        -   Bind the button click to `session.refine_current_node`.
    -   Wrap the whole thing in `pn.LoadingSpinner` bound to `session.is_processing`.

3.  **Step 3: Chat Interface (Optional but Recommended)**
    -   If time permits, replace the TextArea with `pn.chat.ChatInterface` for a better UX (history of refinements).
    -   For Cycle 04, a simple Input/Button is sufficient to meet the spec.

4.  **Step 4: Testing**
    -   Manual verification using the GUI.

## 5. Test Strategy

### Unit Testing Approach (Min 300 words)
-   **ViewModel State:** Test `refine_current_node` with a mock engine.
    -   Assert `is_processing` becomes True, then False.
    -   Assert `selected_node` is updated to the returned node.
-   **Error Handling:** Simulate an engine error. Assert `is_processing` resets to False and (ideally) an error message param is set.

### Integration Testing Approach (Min 300 words)
-   **Full Stack Test:**
    -   Launch the full application in a test environment (headless or via `playwright`).
    -   Select a node.
    -   Input text into the refinement box.
    -   Click "Refine".
    -   Wait for the spinner to disappear.
    -   Verify the text on screen has changed.
    -   Verify the database has the new text (by inspecting the DB file directly after the test).
    -   This confirms the full loop: UI -> ViewModel -> Engine -> Agent -> DB -> UI.
