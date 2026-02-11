# Cycle 05: Semantic Zooming & Refinement (Final Polish) - User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios correspond to the final user experience goals.

### Scenario 5.1: Interactive Refinement (Chat)
**Priority:** Critical
**Goal:** Verify the user can rewrite a node using natural language.

**Steps:**
1.  **Setup:** Launch app. Select any node (e.g., L2 Knowledge).
2.  **Action:** In the Chat input, type "Summarize this in one sentence."
3.  **Verify:** A spinner/loading indicator appears.
4.  **Verify:** The node text updates to a single sentence.
5.  **Verify:** The ID of the node remains unchanged (check via tooltip or debug log).

### Scenario 5.2: Source Verification (Trust)
**Priority:** High
**Goal:** Verify the user can see the evidence backing a summary.

**Steps:**
1.  **Setup:** Select a node (e.g., L3 Action).
2.  **Action:** Click the "Source" tab or button.
3.  **Verify:** A list of text segments appears.
4.  **Verify:** These segments correspond to the children of the selected node (either lower-level summaries or raw chunks).
5.  **Action:** (Manual) Read the source to confirm the summary is accurate.

### Scenario 5.3: Semantic Zooming Full Flow
**Priority:** Critical
**Goal:** The "Aha! Moment".

**Steps:**
1.  **Setup:** Start at Root (Wisdom).
2.  **Action:** Read the aphorism.
3.  **Action:** Click to expand/zoom into a specific concept (Knowledge).
4.  **Action:** Read the explanation.
5.  **Action:** Click to zoom into concrete steps (Action).
6.  **Action:** Read the checklist.
7.  **Action:** Click "Source" to see the raw text.
8.  **Verify:** The navigation was smooth and logical.

## 2. Behavior Definitions (Gherkin)

### Feature: Interactive Chat

```gherkin
Feature: Node Refinement Chat
  As a user
  I want to chat with the summary node
  So that I can refine it iteratively

  Scenario: Sending a refinement instruction
    Given I have selected a node
    And I type "Make it funnier" into the chat
    When I press Send
    Then the system should process the request
    And the node text should update with a humorous version
    And the chat history should be preserved
```

### Feature: Source Traceability

```gherkin
Feature: Source Verification
  As a user
  I want to see the source of a summary
  So that I can trust the AI's output

  Scenario: Viewing Source Chunks
    Given I have selected a node
    When I activate the Source View
    Then I should see the text of the child nodes
    And I should be able to navigate to them if they are summaries
```
