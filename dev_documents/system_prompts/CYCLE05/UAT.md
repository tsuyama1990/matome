# Cycle 05 User Acceptance Test (UAT): Semantic Zooming & Final Polish

## 1. Test Scenarios

### Scenario ID: C05-01 (Semantic Zooming Navigation)
**Priority**: High
**Objective**: Verify that the user can drill down from Wisdom to Action.
**Description**:
As a learner, I want to explore the knowledge tree layer by layer.
**Steps**:
1.  Open `matome canvas`.
2.  **Level 1**: Verify the Root Node ("Wisdom") is visible.
3.  **Action**: Click the Root Node.
4.  **Observation**: A set of "Knowledge" nodes appears.
5.  **Action**: Click one "Knowledge" node.
6.  **Observation**: A set of "Action" nodes appears.

### Scenario ID: C05-02 (Interactive Refinement Chat)
**Priority**: High
**Objective**: Verify that the user can rewrite a node using natural language.
**Description**:
As a user, I want to simplify a confusing node.
**Steps**:
1.  Select a "Knowledge" node.
2.  In the Chat Panel, type: "Explain this using a cooking analogy."
3.  Click Send.
4.  **Observation**:
    -   A loading spinner appears.
    -   The Chat history shows the user message.
    -   After a few seconds, the Node Card text updates with a cooking analogy.
    -   The Chat history shows a system confirmation ("Updated node...").

### Scenario ID: C05-03 (Source Verification)
**Priority**: Medium
**Objective**: Verify that the user can check the original text.
**Description**:
As a skeptic, I want to see the evidence for a claim.
**Steps**:
1.  Drill down to a Leaf Node (Action/Data).
2.  Look for a "Show Source" button/icon in the Detail View.
3.  Click it.
4.  **Observation**: A panel reveals the raw text chunk(s) that generated this summary.

## 2. Behavior Definitions (Gherkin)

### Feature: Drill-Down Navigation

**Scenario**: Expanding a Node
  **GIVEN** the user is viewing the Wisdom node
  **WHEN** the user clicks on the node
  **THEN** the system should fetch the children of that node
  **AND** render them visually below the parent
  **AND** the layout should adjust to fit the new content

### Feature: Chat Refinement

**Scenario**: Rewriting Node Content
  **GIVEN** a selected node with text "Complexity is bad"
  **WHEN** the user sends the instruction "Elaborate on why" via Chat
  **THEN** the system should generate a new summary
  **AND** the node text should update to "Complexity is bad because..."
  **AND** the node's `is_user_edited` flag should be True
