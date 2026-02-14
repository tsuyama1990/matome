# Cycle 03 UAT: GUI Visualization Verification

## 1. Test Scenarios

### Scenario ID: UAT-C03-01 - Launch & Pyramid View
**Priority:** High
**Description:**
Verify that the `matome serve` command launches the Panel application and displays the correct Root Node (Wisdom).
**Steps:**
1.  Run `uv run matome serve results/chunks.db`.
2.  Open the displayed localhost URL (e.g., `http://localhost:5006/matome`).
3.  Check the top of the screen.
**Expected Result:**
-   The Root Node text (Wisdom) is visible.
-   The node should be labeled "Level: Wisdom".
-   No error messages in the console.

### Scenario ID: UAT-C03-02 - Drill Down
**Priority:** High
**Description:**
Verify that clicking a node expands its children, allowing navigation from Wisdom to Knowledge to Information.
**Steps:**
1.  Launch the app.
2.  Click on the Root Node or its "Expand" button.
3.  Look for child nodes (Knowledge) appearing below it.
4.  Click on a Knowledge node.
5.  Look for its children (Information) appearing below it.
**Expected Result:**
-   The UI updates responsively.
-   Breadcrumbs should update (e.g., "Home > Wisdom > Knowledge").
-   The structure should match the database content.

### Scenario ID: UAT-C03-03 - Detail View
**Priority:** Medium
**Description:**
Verify that selecting a node shows its full details in a separate pane/area.
**Steps:**
1.  Click on any node in the tree view.
2.  Inspect the "Details" panel (usually on the right or bottom).
**Expected Result:**
-   The full text of the node is displayed.
-   Metadata (e.g., `dikw_level`) is shown.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Interactive Visualization

  Scenario: User Opens Canvas
    Given a valid "chunks.db" with a DIKW tree
    When I run "matome serve" and open the browser
    Then I should see the Root Node labeled as "Wisdom"
    And I should see the full text of the Wisdom node

  Scenario: User Drills Down
    Given the Canvas is open at the Root level
    When I click on the Root Node
    Then the children nodes (Level: Knowledge) should be displayed
    And the breadcrumbs should update to show the path

  Scenario: User Inspects Details
    Given I have navigated to a Leaf Node (Information)
    When I select the node
    Then I should see its full text content in the detail view
    And I should see its metadata indicating "dikw_level": "information"
```
