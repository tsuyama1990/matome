# Cycle 03 User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios validate that the backend correctly handles interactive requests, maintaining data integrity and concurrency safety.

### Scenario 03-A: Single Node Refinement
**Priority:** Critical
**Description:** Verify that a user can update the summary of a specific node by providing instructions.
**Procedure:**
1.  Initialize `InteractiveRaptorEngine` connected to a test DB.
2.  Pick an existing node (e.g., ID "node_123") with summary "Original Text".
3.  Call `engine.refine_node("node_123", "Rewrite as a pirate")`.
4.  Mock the agent to return "Pirate Text".
5.  Fetch the node again from the DB.
**Pass Criteria:**
*   Node summary is now "Pirate Text".
*   `metadata.is_user_edited` is `True`.
*   `metadata.refinement_history` contains "Rewrite as a pirate".

### Scenario 03-B: Concurrency Stress Test
**Priority:** High
**Description:** Ensure that the database remains consistent even when multiple operations occur simultaneously (simulating CLI writing while GUI reads/writes).
**Procedure:**
1.  Start a background thread that continuously reads random nodes from the DB.
2.  Start another background thread that continuously updates random nodes via `refine_node`.
3.  Run for 10 seconds.
**Pass Criteria:**
*   No "database is locked" exceptions.
*   The final DB state is consistent (e.g., no partial writes).

### Scenario 03-C: Child Node Retrieval
**Priority:** Medium
**Description:** Verify that the engine correctly retrieves the children of a given node for drill-down functionality.
**Procedure:**
1.  Create a parent node P and two children C1, C2 in the DB. Link them via edges.
2.  Call `engine.get_children(P.id)`.
**Pass Criteria:**
*   Returns a list containing exactly C1 and C2.
*   The returned objects are full `SummaryNode` instances.

## 2. Behavior Definitions (Gherkin)

### Feature: Interactive Refinement

```gherkin
Feature: Node Refinement
  As a user
  I want to give instructions to rewrite a specific summary node
  So that I can tailor the knowledge base to my understanding

  Scenario: Refining a node
    Given a node with ID "123" and summary "Complex explanation"
    When I request to refine node "123" with instruction "Make it simple"
    Then the system should generate a new summary based on "Complex explanation" and "Make it simple"
    And the node "123" in the database should be updated with the new summary
    And the node "123" should be marked as user-edited
```

### Feature: Drill-Down Navigation

```gherkin
Feature: Node Navigation
  As a user
  I want to see the children of a summary node
  So that I can drill down into the details (Semantic Zooming)

  Scenario: Retrieving children
    Given a parent node "Wisdom_1" linked to children "Knowledge_A" and "Knowledge_B"
    When I request the children of "Wisdom_1"
    Then the system should return a list containing "Knowledge_A" and "Knowledge_B"
```
