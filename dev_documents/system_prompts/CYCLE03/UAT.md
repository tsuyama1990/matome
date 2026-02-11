# Cycle 03 User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario 03-A: Interactive Refinement of Nodes
**Priority:** High
**Goal:** Verify that the `InteractiveRaptorEngine` allows programmatic updating of specific nodes based on user instructions, simulating the "Refine" action in the future GUI.

**Description:**
This scenario validates the core functionality of the interactive engine: taking an existing node from the database, applying a user's refinement instruction (e.g., "Make it simpler"), and saving the updated version back to the database. This must happen without re-processing the entire tree.

**Execution Steps (Python Script):**
1.  **Setup:**
    *   Load an existing `chunks.db` (populated in previous cycles).
    *   Initialize `InteractiveRaptorEngine` with a store and agent.
    *   Pick a target node ID (e.g., a Level 1 node).
    *   Read the original text: `original_text = store.get_node(target_id).text`.
2.  **Action:**
    *   Call `engine.refine_node(target_id, instruction="Rewrite this as if explaining to a 5-year-old.")`.
3.  **Verification:**
    *   Fetch the node again: `updated_node = store.get_node(target_id)`.
    *   **Content Change:** Assert `updated_node.text != original_text`.
    *   **Metadata Update:** Assert `updated_node.metadata.is_user_edited == True`.
    *   **History Update:** Assert `updated_node.metadata.prompt_history[-1]` contains the instruction.

**Success Criteria:**
*   The node is updated in place.
*   The metadata reflects the manual edit.
*   No other nodes are affected.

### Scenario 03-B: Concurrent Access Stability
**Priority:** Critical
**Goal:** Ensure that the `DiskChunkStore` can handle simultaneous read and write operations without locking or crashing, which is essential for a responsive GUI.

**Description:**
In a real GUI session, the user might be browsing the tree (reads) while a background task is generating summaries (writes), or multiple users might be accessing the same database (if deployed as a server). This stress test simulates such a load.

**Execution Steps (Python Script):**
1.  **Setup:**
    *   Create a `chunks.db` with 100+ nodes.
    *   Define a `reader_task`: Randomly reads nodes in a loop.
    *   Define a `writer_task`: Randomly updates nodes in a loop.
2.  **Action:**
    *   Spawn 5 `reader_threads` and 2 `writer_threads`.
    *   Run them concurrently for 10 seconds.
3.  **Verification:**
    *   Check for exceptions (e.g., `sqlite3.OperationalError: database is locked`).
    *   Check data integrity: After threads stop, verify all nodes can be read.

**Success Criteria:**
*   Zero exceptions raised during the run.
*   The database remains consistent and readable after the test.

## 2. Behavior Definitions (Gherkin)

### Feature: Single Node Refinement

**Scenario: Updating a Node with Instructions**
  Given an initialized `InteractiveRaptorEngine`
  And an existing node with ID "node-123" containing text "Complex academic explanation."
  When I call `refine_node` on "node-123" with instruction "Simplify this."
  Then the agent should generate a new summary based on "Simplify this."
  And the node "node-123" in the store should be updated with the new text
  And the node's `is_user_edited` flag should be set to true
  And the instruction "Simplify this." should be recorded in `prompt_history`

### Feature: Concurrency Safety

**Scenario: Simultaneous Read and Write**
  Given a `DiskChunkStore` configured for concurrency (WAL mode)
  When multiple threads attempt to read and write to the store simultaneously
  Then no "database is locked" errors should occur
  And all write operations should eventually be committed
  And all read operations should return valid data
