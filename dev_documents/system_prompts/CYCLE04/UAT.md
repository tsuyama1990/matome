# Cycle 04: GUI Foundation (MVVM) - User Acceptance Test (UAT)

## 1. Test Scenarios

### Scenario 4.1: Application Launch
**Objective**: Ensure the web application starts and connects to the backend without error.
*   **Description**:
    1.  Ensure `chunks.db` exists with some data.
    2.  Run `python -m matome.ui.app`.
    3.  Open browser.
*   **Success Criteria**:
    *   The page loads within 5 seconds.
    *   The title "Matome Canvas" is visible.
    *   The sidebar displays a tree structure (even if simplistic).

### Scenario 4.2: Node Navigation (Read-Only)
**Objective**: Verify that clicking a node in the sidebar updates the main view.
*   **Description**: Click the root node ("Wisdom"), then click a leaf node ("Action").
*   **Success Criteria**:
    *   The main content area updates instantly (< 200ms).
    *   The title of the main area matches the selected node ID.
    *   The text matches the content in the database.

### Scenario 4.3: State Persistence (Session Scope)
**Objective**: Verify that the ViewModel correctly holds state during a session.
*   **Description**: Select a node, reload the page (if state persistence is implemented, otherwise just navigate away and back).
*   **Success Criteria**:
    *   (Basic): The app doesn't crash on rapid navigation.
    *   (Advanced): If URL routing is used, reloading the page with `?node=id` restores the view.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Matome Canvas Basic Navigation

  Scenario: Loading the Application
    GIVEN a populated chunks.db
    WHEN I launch the Matome UI
    THEN I should see the application title
    AND I should see the root node in the sidebar

  Scenario: Selecting a Node
    GIVEN the application is loaded
    WHEN I click on a node in the sidebar
    THEN the main view should display the node's text
    AND the view model's current_node should update
```
