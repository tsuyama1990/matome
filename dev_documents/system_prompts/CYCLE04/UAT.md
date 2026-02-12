# Cycle 04 User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios validate that the GUI foundation is correctly established, focusing on the MVVM separation and the ability to launch the Panel server.

### Scenario 04-A: Interactive Session State (ViewModel Test)
**Priority:** High
**Description:** Verify that the `InteractiveSession` correctly manages the application state without needing a UI.
**Procedure:**
1.  Initialize `InteractiveRaptorEngine` with mocked data.
2.  Initialize `InteractiveSession(engine=mock_engine)`.
3.  Call `session.select_node("node_1")`.
4.  Assert `session.selected_node.id == "node_1"`.
5.  Call `session.load_initial_state()`.
6.  Assert `session.current_root` is not None.
**Pass Criteria:**
*   The `param` variables update correctly.
*   The engine calls are made as expected.

### Scenario 04-B: GUI Launch & Wisdom Display (Manual)
**Priority:** Critical
**Description:** Verify that the `matome canvas` command launches a browser and displays the correct initial content.
**Procedure:**
1.  Ensure `chunks.db` exists with a Wisdom node.
2.  Run `matome canvas`.
3.  Observe the browser window.
**Pass Criteria:**
*   The Panel server starts without errors.
*   The browser opens to `http://localhost:5006` (or similar).
*   The text of the Wisdom node is clearly visible on the screen.

### Scenario 04-C: Component Reactivity (Manual)
**Priority:** Medium
**Description:** Verify that updating the model updates the view.
**Procedure:**
1.  (Requires dev tools or a script) Inject a change into the `session.current_root` (e.g., modify its summary).
2.  Observe if the `WisdomCard` updates automatically.
**Pass Criteria:**
*   The UI reflects the new text immediately.

## 2. Behavior Definitions (Gherkin)

### Feature: GUI Initialization

```gherkin
Feature: Canvas Launch
  As a user
  I want to start the Matome Canvas interface
  So that I can visualize the knowledge tree

  Scenario: Starting the server
    Given a valid "chunks.db" file with a root node
    When I run the command "matome canvas"
    Then the Panel server should start
    And the application should load the root node into the session
    And the UI should display the Wisdom card
```
