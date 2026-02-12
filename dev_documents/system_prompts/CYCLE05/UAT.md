# Cycle 05 User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios validate the complete "Knowledge Installation" experience, ensuring the user can seamlessly navigate and refine the knowledge tree.

### Scenario 05-A: Semantic Zooming (Drill-Down)
**Priority:** Critical
**Description:** Verify that clicking a parent node correctly loads and displays its children.
**Procedure:**
1.  Launch `matome canvas`.
2.  Observe the Wisdom node (L1).
3.  Click the Wisdom node (or a "View Details" button).
4.  Observe the content area.
**Pass Criteria:**
*   The UI updates to show a list of Knowledge nodes (L2).
*   The text of the Knowledge nodes corresponds to the semantic logic of the Wisdom node.
*   Clicking a Knowledge node further reveals Information nodes (L3).

### Scenario 05-B: Interactive Refinement (GUI)
**Priority:** High
**Description:** Verify that the refinement chat interface works as expected.
**Procedure:**
1.  Select a specific node in the UI.
2.  Focus on the "Refine" chat box.
3.  Type: "Rewrite this as a haiku." and submit.
4.  Wait for the process to complete (spinner/loading indicator).
5.  Observe the node's text.
**Pass Criteria:**
*   The node's text updates to a haiku format.
*   The change persists if the page is refreshed.
*   The `refinement_history` shows the instruction.

### Scenario 05-C: "Emin's Shikihou" Full Walkthrough
**Priority:** Medium
**Description:** Execute the core user story defined in `USER_TEST_SCENARIO.md`.
**Procedure:**
1.  Load the `emin_shikihou.txt` data.
2.  Follow the steps: See Wisdom -> Zoom In -> Refine.
**Pass Criteria:**
*   **Aha! Moment:** The user feels they grasped the book's core message immediately.
*   **Zoom-In Thrill:** The detailed nodes provide the "Why" and "How" clearly.
*   **Customization:** The user successfully modifies a node to fit their mental model.

## 2. Behavior Definitions (Gherkin)

### Feature: Drill-Down Navigation

```gherkin
Feature: Semantic Zooming
  As a user
  I want to explore the details behind a high-level summary
  So that I can verify the logic and actionable steps

  Scenario: Drilling down from Wisdom to Knowledge
    Given the Wisdom node is displayed
    When I click on the Wisdom node
    Then the system should display the associated Knowledge nodes
    And the Wisdom node should remain visible as context (e.g., in a breadcrumb or header)
```

### Feature: Interactive Refinement

```gherkin
Feature: Chat-based Refinement
  As a user
  I want to rewrite a specific part of the knowledge tree
  So that it matches my preferred learning style

  Scenario: Refining a node via chat
    Given I have selected a node "Investment Rule #1"
    When I type "Explain like I'm 5" into the refinement chat
    And I click "Send"
    Then the system should rewrite "Investment Rule #1" using simple language
    And the UI should update to display the new text
```
