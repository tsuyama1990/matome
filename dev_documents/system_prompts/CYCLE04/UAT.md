# Cycle 04: User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios verify the correctness of the **GUI Foundation (MVVM)**.

### Scenario 1: ViewModel Initialization
**Priority**: High
**Goal**: Verify that `InteractiveSession` correctly loads the initial state from the engine.
- **Steps**:
  1. Prepare a `chunks.db` with a known root node.
  2. Instantiate `InteractiveRaptorEngine` and `InteractiveSession(engine, root_id)`.
  3. Verify `session.current_node` is not None and matches the root node.
  4. Verify `session.child_nodes` contains the expected children.
  5. Verify `session.status_message` indicates "Loaded".

### Scenario 2: Reactive State Updates (Programmatic)
**Priority**: Critical
**Goal**: Verify that changing the ViewModel state triggers updates in the View logic (simulated).
- **Steps**:
  1. Create a `MatomeCanvas(session)`.
  2. Manually change `session.current_node` to a new dummy node.
  3. Call the dependent method `canvas.main_content_view()`.
  4. Inspect the returned Panel object (e.g., check `object.object` for Markdown text).
  5. Verify it displays the text of the *new* dummy node.

## 2. Behavior Definitions (Gherkin)

### Feature: Reactive UI State

**Scenario: Loading a Node**
  GIVEN an `InteractiveSession` connected to a valid engine
  WHEN I call `session.load_node('node_X')`
  THEN `session.is_loading` should briefly become `True`
  AND `session.current_node` should eventually update to the object for `node_X`
  AND `session.child_nodes` should update to the children of `node_X`
  AND `session.is_loading` should return to `False`.

**Scenario: View Updates**
  GIVEN a `MatomeCanvas` bound to a session
  WHEN `session.current_node` changes
  THEN the main content area of the canvas must re-render to display the new node's details.
