# Cycle 03 User Acceptance Testing (UAT)

## 1. Test Scenarios

Cycle 03 introduces the interactive capabilities. The UAT focuses on verifying that user-driven changes to the knowledge graph are correctly applied and persisted.

### Scenario CYCLE03-01: Single Node Refinement
**Priority:** High
**Description:** Verify that a user can successfully update the text of a single node.
**Steps:**
1.  **Preparation:** Load an existing `chunks.db` (e.g., from Cycle 02).
2.  **Execution:** Use a Python script to instantiate `InteractiveRaptorEngine` and call `refine_node(node_id="target_id", instruction="Make it simpler")`.
3.  **Verification:** Retrieve the node again using `get_node("target_id")`.
4.  **Result Check:** The text should be different (presumably simpler), and `metadata.refinement_history` should contain the instruction.

### Scenario CYCLE03-02: Persistence & Isolation
**Priority:** High
**Description:** Verify that changes persist across engine restarts and do not affect other nodes.
**Steps:**
1.  **Preparation:** Note the content of node A and node B. Refine node A.
2.  **Restart:** Restart the Python process/kernel.
3.  **Verification:** Check node A and node B.
4.  **Result Check:** Node A should reflect the refinement. Node B should remain identical to the original state.

### Scenario CYCLE03-03: Concurrent Access Stress Test
**Priority:** Medium
**Description:** Verify that the database does not lock up under load.
**Steps:**
1.  **Preparation:** Use a script that spawns 5 threads, each refining a different node simultaneously.
2.  **Execution:** Run the script.
3.  **Verification:** Check for `sqlite3.OperationalError` in logs.
4.  **Result Check:** All 5 refinements should succeed.

**Jupyter Notebook:** `tutorials/CYCLE03_Interactive_Backend.ipynb`

## 2. Behavior Definitions

### Feature: Interactive Refinement

**Scenario:** Successful Refinement
    **Given** a node with text "Complexity theory is hard."
    **And** an `InteractiveRaptorEngine`
    **When** the user instructs "Explain it like I'm 5"
    **Then** the node text should change to something like "Complexity is like a puzzle."
    **And** the metadata `is_user_edited` should be `True`
    **And** the instruction should be logged in `refinement_history`

**Scenario:** Non-Existent Node
    **Given** an invalid `node_id` "ghost_node"
    **When** `refine_node` is called
    **Then** it should raise a `KeyError` or `ValueError` gracefully.
