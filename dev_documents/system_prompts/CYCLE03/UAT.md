# Cycle 03: User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario A: Verify Backend Refinement
*   **ID**: S03-01
*   **Priority**: High
*   **Description**: Verify that the `InteractiveRaptorEngine` can successfully refine a specific node and persist the changes.
*   **Preconditions**:
    *   System built with `InteractiveRaptorEngine` and `RefinementStrategy`.
    *   `chunks.db` exists with at least one summary node.
*   **Steps (Scripted)**:
    1.  Initialize `DiskChunkStore` and `InteractiveRaptorEngine`.
    2.  Retrieve an existing Summary Node (e.g., ID "node_123").
    3.  Call `refine_node("node_123", "Rewrite this to be funnier")`.
    4.  Reload the node from the database.
    5.  **Check**: Is the text different?
    6.  **Check**: Is `dikw_level` preserved?
    7.  **Check**: Is `is_user_edited` True?
    8.  **Check**: Does `refinement_history` contain "Rewrite this to be funnier"?

### Scenario B: Verify Concurrent Access (Simulated GUI Load)
*   **ID**: S03-02
*   **Priority**: Medium
*   **Description**: Ensure the database doesn't lock up or crash when read and written to simultaneously (simulating CLI batch process + GUI interaction).
*   **Preconditions**:
    *   `chunks.db` exists.
*   **Steps**:
    1.  Run `concurrent_test.py` (which spawns 2 threads).
    2.  Thread 1 (Reader): Loops `store.get_all_nodes()` every 0.1s.
    3.  Thread 2 (Writer): Loops `store.save_node(new_node)` every 0.5s.
    4.  Run for 10 seconds.
    5.  **Check**: No `sqlite3.OperationalError` or unhandled exceptions.

## 2. Behavior Definitions (Gherkin)

### Feature: Interactive Refinement

**Scenario: User refines a node via Engine**
  **GIVEN** an existing summary node with text "Original Summary"
  **WHEN** `InteractiveRaptorEngine.refine_node` is called with instruction "Make shorter"
  **THEN** the summarization agent should be invoked with `RefinementStrategy`
  **AND** the node text should be updated
  **AND** the node metadata `is_user_edited` should be set to `True`
  **AND** the instruction should be appended to `refinement_history`
  **AND** the changes should be saved to `chunks.db`
