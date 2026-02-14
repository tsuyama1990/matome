# Cycle 04 UAT: Interactive Refinement Verification

## 1. Test Scenarios

### Scenario ID: UAT-C04-01 - User Refines a Node
**Priority:** High
**Description:**
Verify that a user can update a node's text by issuing an instruction via the UI.
**Steps:**
1.  Navigate to a "Knowledge" node.
2.  In the "Refine" text area, type: "Translate this summary to Japanese."
3.  Click the "Refine" button.
4.  Wait for the spinner to stop.
**Expected Result:**
-   The text in the detail view should change to Japanese (assuming LLM works).
-   The `is_user_edited` flag (visible in metadata section if implemented) should be True.
-   The change should be immediate.

### Scenario ID: UAT-C04-02 - UI Responsiveness
**Priority:** Medium
**Description:**
Verify that the UI indicates processing status during refinement.
**Steps:**
1.  Click "Refine" on any node.
2.  Observe the UI while waiting.
**Expected Result:**
-   The "Refine" button should be disabled.
-   A loading spinner or indicator should be visible.
-   The UI should not crash or freeze completely (browser might be responsive, app shows loading).

### Scenario ID: UAT-C04-03 - Persistence Check
**Priority:** High
**Description:**
Verify that changes made in the UI persist after a page reload.
**Steps:**
1.  Perform a refinement (Scenario 1).
2.  Refresh the browser page.
3.  Navigate back to the same node.
**Expected Result:**
-   The text should still be the refined version (Japanese).
-   This confirms the database update was successful.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: User-Driven Knowledge Refinement

  Scenario: Refine Node Content
    Given I am viewing a Knowledge Node in the Matome Canvas
    When I enter "Simplify this explanation" into the refinement box
    And I click the "Refine" button
    Then the system should show a loading indicator
    And the node text should update to a simplified version within 10 seconds
    And the new text should be saved to the database

  Scenario: Error Handling during Refinement
    Given the backend LLM service is down (simulated)
    When I attempt to refine a node
    Then the system should display an error message
    And the original node text should remain unchanged
    And the loading indicator should disappear
```
