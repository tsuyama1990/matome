# Cycle 05 UAT: Traceability & Final Release Verification

## 1. Test Scenarios

### Scenario ID: UAT-C05-01 - Source Verification
**Priority:** High
**Description:**
Verify that clicking "Show Source" on a node reveals the original chunks (Level 0) that contributed to it.
**Steps:**
1.  Navigate to an "Information" node (Leaf Summary).
2.  Click the "Show Source" button.
3.  Check the displayed modal/panel.
**Expected Result:**
-   A list of raw text chunks should appear.
-   The text should match content from the original input file.
-   The IDs or indices of the chunks should be consistent with the summary's children.

### Scenario ID: UAT-C05-02 - Tutorial Execution
**Priority:** Critical
**Description:**
Verify that the `tutorials/UAT_AND_TUTORIAL.py` Marimo notebook runs successfully from start to finish.
**Steps:**
1.  Run `uv run marimo edit tutorials/UAT_AND_TUTORIAL.py` (or execute via CLI).
2.  Execute all cells.
**Expected Result:**
-   No runtime errors.
-   The final output should indicate "All UAT Scenarios Passed".
-   The generated tree visualization should be correct.

### Scenario ID: UAT-C05-03 - Visual Polish
**Priority:** Low
**Description:**
Verify that the UI is aesthetically pleasing and functional.
**Steps:**
1.  Open the app in a browser.
2.  Resize the window.
3.  Check for overlapping text or broken layouts.
**Expected Result:**
-   Layout adjusts reasonably well (responsive).
-   Colors and fonts are consistent.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Traceability & Trust

  Scenario: User Verifies Summary Source
    Given I am viewing a summary node "S1"
    When I click "Show Source Chunks"
    Then the system should display a list of original text fragments
    And these fragments should belong to the subtree of "S1"
    And the user should be able to read the raw evidence

  Scenario: User Runs Tutorial
    Given the "UAT_AND_TUTORIAL.py" notebook
    When I execute the notebook
    Then all cells should complete without error
    And the final cell should print "UAT PASSED"
```
