# Cycle 03: Interactive Engine & DB Concurrency - User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario ID: C03-01 - Single Node Refinement
**Priority:** High
**Goal:** Verify that a user can ask to "refine" a single node and it updates in the database.
**Description:** Use a script to instantiate `InteractiveRaptorEngine`, select a node ID, and call `refine_node(node_id, "Make it simpler")`. Verify the node's text changes and `is_user_edited` becomes True.
**Prerequisites:**
-   Existing `chunks.db` with at least one node.
-   `OPENAI_API_KEY` set.

### Scenario ID: C03-02 - Concurrency Stress Test
**Priority:** High
**Goal:** Ensure database integrity under load (simulating multiple UI actions).
**Description:** Use a script to spawn 5 threads, each attempting to update different nodes simultaneously. Check for exceptions or data loss.
**Prerequisites:** None.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Interactive Refinement

  Scenario: Refine Node Request
    GIVEN a node with ID "N1" exists in the database
    AND the node text is "Complexity is high."
    WHEN I call refine_node("N1", instruction="Make it simpler")
    THEN the node text should change to something simpler
    AND the node metadata "is_user_edited" should be true

  Scenario: Concurrent Updates
    GIVEN a database with 10 nodes
    WHEN 5 threads try to update different nodes simultaneously
    THEN all updates should succeed without "database locked" error
```
