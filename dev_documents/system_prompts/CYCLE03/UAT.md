# Cycle 03 User Acceptance Test (UAT): Interactive Engine & Concurrency

## 1. Test Scenarios

### Scenario ID: C03-01 (Single Node Refinement)
**Priority**: High
**Objective**: Verify that the "Refinement" API works end-to-end (DB Read -> LLM -> DB Write).
**Description**:
As a developer, I need to ensure that when I ask the `InteractiveRaptorEngine` to refine a node, it actually updates the database record.
**Steps**:
1.  Create `tests/uat/C03_refinement_check.ipynb`.
2.  **Setup**: Create a DB with one node: "Original Text".
3.  **Execute**: Call `engine.refine_node(id, "Add exclamation")`.
    -   (Mock the LLM to return "Original Text!")
4.  **Verify**:
    -   Fetch the node again using a *fresh* engine instance.
    -   Assert text == "Original Text!".
    -   Assert `metadata.is_user_edited` == True.

### Scenario ID: C03-02 (Concurrent Stress Test)
**Priority**: Critical
**Objective**: Verify that the system is stable under multi-threaded load (simulating a busy UI).
**Description**:
As a user, I don't want the app to crash with "Database Locked" errors if I browse while an update is saving.
**Steps**:
1.  Create `tests/uat/C03_concurrency_check.ipynb`.
2.  **Setup**: A large DB (1000 nodes).
3.  **Action**:
    -   Spawn a "Reader Thread" that performs `get_tree_structure()` every 100ms.
    -   Spawn a "Writer Thread" that performs `refine_node()` (with mock delay) every 500ms.
4.  **Observe**: Run for 10 seconds.
5.  **Pass Criteria**: No unhandled exceptions in the log.

## 2. Behavior Definitions (Gherkin)

### Feature: Node Refinement

**Scenario**: User refines a node
  **GIVEN** a node with ID "123" and text "Hello"
  **WHEN** I call `refine_node("123", "Make it uppercase")`
  **THEN** the LLM should be invoked with the instruction
  **AND** the node in the database should be updated to "HELLO"
  **AND** the `is_user_edited` flag should be set to True

### Feature: Database Concurrency

**Scenario**: Reading while writing
  **GIVEN** a long-running write transaction is in progress (e.g., updating a summary)
  **WHEN** another thread attempts to read the tree structure
  **THEN** the read operation should succeed immediately (thanks to WAL mode)
  **AND** it should return the data as it was *before* the write transaction started
