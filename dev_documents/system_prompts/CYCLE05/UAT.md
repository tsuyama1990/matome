# Cycle 05: Semantic Zooming Experience - User Acceptance Test (UAT)

## 1. Test Scenarios

### Scenario 5.1: The "Aha! Moment" (Full Walkthrough)
**Objective**: Validate the "Semantic Zooming" user journey from start to finish.
*   **Description**:
    1.  Load the application with a pre-processed book.
    2.  Start at the "Wisdom" level (Root).
    3.  Drill down to a "Knowledge" node.
    4.  Drill down further to an "Action" node.
*   **Success Criteria**:
    *   Navigation is intuitive (click to expand/select).
    *   Content at each level is distinct (Philosophy vs. Framework vs. Checklist).
    *   User feels "empowered" (subjective, but key).

### Scenario 5.2: Interactive Refinement (Chat)
**Objective**: Confirm that the chat interface correctly triggers node updates.
*   **Description**:
    1.  Select a specific node.
    2.  Type "Summarize this in 3 bullet points" in the chat.
    3.  Wait for completion.
*   **Success Criteria**:
    *   The node's text updates to a bulleted list.
    *   The chat history shows the user's request and a system confirmation.
    *   The database is updated (verify by reloading the app).

### Scenario 5.3: Source Traceability
**Objective**: Ensure users can verify AI claims against the original text.
*   **Description**:
    1.  Select a node that makes a specific claim.
    2.  Click the "Sources" tab/button.
    3.  Read the displayed chunk(s).
*   **Success Criteria**:
    *   The displayed text is the actual source material for that summary node.
    *   No "hallucinated" sources (links to non-existent chunks).

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Semantic Zooming Interface

  Scenario: Navigating the DIKW Pyramid
    GIVEN the Matome Canvas is open
    WHEN I click on the Root Node (Wisdom)
    THEN I should see its children (Knowledge) in the tree
    AND the main view should display the Wisdom text

  Scenario: Refining a Node via Chat
    GIVEN I have selected a node
    WHEN I type "Make it shorter" into the chat input
    AND I press Send
    THEN a loading indicator should appear
    AND the backend should process the refinement
    AND the node text should update in the view
    AND a confirmation message should appear in the chat

  Scenario: Viewing Source Chunks
    GIVEN I have selected a summary node
    WHEN I click the "Sources" tab
    THEN I should see the raw text chunks that contributed to this summary
```
