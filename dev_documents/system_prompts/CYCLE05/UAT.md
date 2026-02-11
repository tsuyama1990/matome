# Cycle 05: Semantic Zooming & Interactive Refinement - User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario ID: C05-01 - Semantic Zoom (Drill Down)
**Priority:** High
**Goal:** Verify that the "Knowledge Tree" expands correctly.
**Description:**
1.  Launch the app. Only the Gold "Wisdom" node is visible.
2.  Click the Wisdom node.
3.  Expected: 3-5 Blue "Knowledge" nodes appear below it.
4.  Click a Knowledge node.
5.  Expected: 3-5 Green "Action" nodes appear below that.
**Prerequisites:**
-   `chunks.db` with a full tree structure.

### Scenario ID: C05-02 - Interactive Refinement (Chat)
**Priority:** High
**Goal:** Verify that the chat interface updates the node text.
**Description:**
1.  Select a "Knowledge" node.
2.  In the "Refine" chat box, type "Rewrite this for a 5-year-old".
3.  Click Send.
4.  Expected: A "Thinking..." indicator appears.
5.  Expected: After ~5 seconds, the node text updates to simpler language.
6.  Expected: The change persists if you refresh the page.
**Prerequisites:**
-   `OPENAI_API_KEY` set.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Semantic Zooming & Refinement

  Scenario: Drill Down Hierarchy
    GIVEN the root node is displayed
    WHEN I click the root node
    THEN the child nodes (Knowledge) should appear
    AND the child nodes should have distinct styling

  Scenario: Refine Node Text
    GIVEN a selected node with text "Complex Theory"
    WHEN I submit "Simplify" in the chat input
    THEN the system should process the request
    AND the selected node text should update to "Simple Idea"
    AND the update should be saved to the database
```
