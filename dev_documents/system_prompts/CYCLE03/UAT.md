# Cycle 03: Interactive Backend - User Acceptance Test (UAT)

## 1. Test Scenarios

### Scenario 3.1: Single Node Refinement
**Objective**: Verify that a user instruction can alter the content of a specific node without affecting the rest of the tree.
*   **Description**:
    1.  Pick an existing summary node (e.g., from Cycle 02 output).
    2.  Call `InteractiveRaptorEngine.refine_node(node_id, "Translate to Japanese")`.
    3.  Inspect the node.
*   **Success Criteria**:
    *   The node's text is now in Japanese.
    *   The node's ID remains the same.
    *   The `metadata.refinement_history` contains the instruction "Translate to Japanese" and the original English text.
    *   Other nodes in the tree are unchanged.

### Scenario 3.2: Concurrent Access Stability
**Objective**: Ensure the backend can handle simultaneous read/write operations, mimicking a busy UI.
*   **Description**:
    1.  Start a script that rapidly queries the root node every 10ms.
    2.  Simultaneously run a script that updates random leaf nodes.
*   **Success Criteria**:
    *   No `sqlite3.OperationalError: database is locked` errors.
    *   The reader script always retrieves valid data (either the old or new version), never a corrupted state.

### Scenario 3.3: History Tracking
**Objective**: Verify that refinement actions are auditable.
*   **Description**: Refine a node twice.
*   **Success Criteria**:
    *   The `refinement_history` list has 2 entries.
    *   The entries are ordered chronologically.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Interactive Node Refinement

  Scenario: Refining a Summary Node
    GIVEN an existing node with text "Original Summary"
    AND an InteractiveRaptorEngine instance
    WHEN I call refine_node with instruction "Make it funnier"
    THEN the agent should use the RefinementStrategy
    AND the node text should be updated to "Funnier Summary"
    AND the original text should be saved in metadata.refinement_history

  Scenario: Concurrent Database Access
    GIVEN a shared DiskChunkStore in WAL mode
    WHEN one thread writes to the database
    AND another thread reads from the database simultaneously
    THEN neither thread should crash
    AND the reader should see consistent data
```
