# Cycle 04: GUI Foundation (MVVM & Basic View) - User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario ID: C04-01 - Launch App & List Nodes
**Priority:** High
**Goal:** Verify that the Panel application launches and displays the root node.
**Description:** Run `matome gui` in the terminal. The browser should open to `http://localhost:5006/app`. The root node (Wisdom) should be visible in the main area.
**Prerequisites:**
-   `chunks.db` exists.
-   `panel` installed.

### Scenario ID: C04-02 - Node Selection (ViewModel Logic)
**Priority:** Medium
**Goal:** Verify that selecting a node updates the detail view.
**Description:** Click on the root node (button or link). The sidebar or detail pane should update to show metadata for that node (e.g., ID, Level).
**Prerequisites:** Same as above.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: GUI Foundation

  Scenario: Launch Application
    GIVEN a valid database "chunks.db"
    WHEN I run the command "matome gui"
    THEN the application server should start
    AND the browser should display the "Matome 2.0" title

  Scenario: View Node Details
    GIVEN the application is running
    AND the root node is displayed
    WHEN I click on the root node
    THEN the detail pane should display the node's text and metadata
```
