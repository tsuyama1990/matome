# Cycle 05: Semantic Zooming Experience - Specification

## 1. Summary

In this final cycle, we will integrate all previous components to deliver the full "Matome 2.0" experience. We will enable the "Semantic Zooming" UI features:
1.  **Pyramid Navigation**: Visual hierarchy of DIKW levels (Wisdom -> Knowledge -> Action).
2.  **Interactive Refinement**: A chat interface in the main view that allows users to refine the currently selected node using natural language instructions.
3.  **Source Verification**: A mechanism to display the original text chunks linked to a summary node.

The `InteractiveSession` ViewModel will be updated to handle chat history and call the `InteractiveRaptorEngine.refine_node` method. The View will be enhanced with `pn.ChatInterface` (or similar) and a more sophisticated tree visualization.

## 2. System Architecture

```text
src/
├── matome/
│   ├── ui/
│   │   ├── **app.py**              # UPDATED: Add chat interface and advanced layout
│   │   ├── **view_model.py**       # UPDATED: Add chat handling logic
│   │   └── components/
│   │       ├── **chat_view.py**    # CREATED: Refinement chat component
│   │       └── **source_view.py**  # CREATED: Source chunk display
tests/
├── **test_e2e.py**                 # CREATED: End-to-end user scenarios
```

### Key Components

*   **`ChatInterface` (UI)**: Allows users to type instructions.
*   **`InteractiveSession` (ViewModel)**: Handles the `send` event from the chat, calls the backend, and updates the view.
*   **`SourceView` (UI)**: A tab or modal that shows the raw text chunks associated with the current summary node.

## 3. Design Architecture

### 3.1. Chat Integration (ViewModel)

```python
class InteractiveSession(param.Parameterized):
    # ... existing params ...
    chat_history = param.List(default=[])

    async def on_chat_input(self, user_input: str, user_instance: str):
        """
        Callback for chat interface.
        1. Append user message to history.
        2. Set loading state.
        3. Call backend to refine node.
        4. Append system response (confirmation) to history.
        5. Update current_node (View reacts automatically).
        """
        if not self.current_node:
            return "Please select a node first."

        self.is_loading = True
        try:
            new_node = await run_in_thread(
                self.engine.refine_node,
                self.current_node.id,
                user_input
            )
            self.current_node = new_node
            return f"Node updated! (ID: {new_node.id})"
        except Exception as e:
            return f"Error: {e}"
        finally:
            self.is_loading = False
```

### 3.2. Source Verification (UI)

We will add a "Sources" tab to the main view.

```python
# pseudo-code for source_view.py
def render_source_view(session: InteractiveSession):
    # Reactive function
    @pn.depends(session.param.current_node)
    def _content(node):
        if not node: return "Select a node."
        chunks = session.engine.get_source_chunks(node.id)
        return pn.Column(*[pn.pane.Markdown(c.text) for c in chunks])

    return pn.panel(_content)
```

## 4. Implementation Approach

### Step 1: Implement Chat View
1.  Create `src/matome/ui/components/chat_view.py`.
2.  Use `pn.chat.ChatInterface` or build a simple list of messages + input box.
3.  Bind the `callback` to `session.on_chat_input`.

### Step 2: Update ViewModel for Refinement
1.  Modify `src/matome/ui/view_model.py`.
2.  Implement `on_chat_input` as an asynchronous method (to keep UI responsive).
3.  Use `concurrent.futures` or `asyncio` to run the blocking `refine_node` call.

### Step 3: Implement Source View
1.  Create `src/matome/ui/components/source_view.py`.
2.  Add a method to `InteractiveRaptorEngine` to fetch source chunks for a given summary node ID (using `metadata.source_chunk_ids`).
3.  Render these chunks in a collapsible list or tab.

### Step 4: Final Polish
1.  Update `src/matome/ui/app.py` to organize components:
    *   Sidebar: Tree Navigation.
    *   Main: Tabs ("Summary", "Sources").
    *   Bottom/Right: Chat Interface.
2.  Apply CSS styling for a cleaner look.

## 5. Test Strategy

### 5.1. E2E Manual Testing (The "User Test Scenario")

**Scenario A: The Aha! Moment**
*   Launch app.
*   See Wisdom node (L1).
*   Expand to see Knowledge nodes (L2).
*   **Pass**: Distinct visual difference or clear hierarchy.

**Scenario B: The Zoom-In Thrill**
*   Select an Action node (L3).
*   Type "Rewrite for a 5-year-old" in chat.
*   **Pass**: Loading spinner appears -> Text updates -> New text is simpler -> Chat confirms "Node updated!".

**Scenario C: Source Verification**
*   Click "Sources" tab.
*   **Pass**: Original text chunks appear. Text matches the source PDF/TXT content.

### 5.2. Automated UI Tests (Optional/Future)
*   Using `playwright` to click buttons and verify text updates would be ideal but might be out of scope for this cycle. We will rely on unit tests for the ViewModel logic.

### 5.3. Performance Test
*   Measure the time from "Send" to "Update".
*   Target: < 10 seconds (LLM dependent) but UI must remain responsive (spinner spinning).
