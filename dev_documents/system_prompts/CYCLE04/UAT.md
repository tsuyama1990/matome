# Cycle 04: GUI Foundation (MVVM) - User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios verify the usability of the initial GUI.

### Scenario 4.1: App Launch & Initial Load
**Priority:** Critical
**Goal:** Verify the application starts and loads data.

**Steps:**
1.  **Setup:** Ensure `chunks.db` is populated (from previous cycles).
2.  **Action:** Run command `panel serve src/matome/interface/app.py` (or wrapper).
3.  **Action:** Open browser to `localhost:5006`.
4.  **Verify:** The application loads.
5.  **Verify:** The "Wisdom" (Root) node is displayed in the main view or sidebar immediately.

### Scenario 4.2: Navigation (Drill Down)
**Priority:** High
**Goal:** Verify Semantic Zooming navigation.

**Steps:**
1.  **Setup:** App is running.
2.  **Action:** Click on a child node in the "Tree Navigator" (e.g., a "Knowledge" node).
3.  **Verify:** The "Detail View" updates to show the text of the selected Knowledge node.
4.  **Verify:** The "Tree Navigator" expands to show the children (Action nodes) of the selected Knowledge node.

### Scenario 4.3: State Consistency
**Priority:** Medium
**Goal:** Ensure the View stays in sync with the ViewModel.

**Steps:**
1.  **Setup:** Select Node A.
2.  **Action:** Click Node B.
3.  **Verify:** Detail View shows Node B text.
4.  **Action:** Click Node A again.
5.  **Verify:** Detail View shows Node A text.

## 2. Behavior Definitions (Gherkin)

### Feature: GUI Navigation

```gherkin
Feature: Matome Canvas Navigation
  As a user
  I want to explore the knowledge tree visualy
  So that I can find relevant information quickly

  Scenario: Viewing the Root
    Given the application is launched
    When the page loads
    Then the Root (Wisdom) summary should be visible
    And the loading indicator should disappear

  Scenario: Selecting a Child Node
    Given I am viewing the Root
    When I click on a Child Node (Knowledge)
    Then the Detail View should update to display the Child's content
    And the Tree View should highlight the selected node
```
