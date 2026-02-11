# Cycle 03: Interactive Engine & Concurrency - User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios verify the backend capabilities required for the GUI: random access and safe updates.

### Scenario 3.1: Single Node Refinement (The "Rewrite")
**Priority:** Critical
**Goal:** Verify that a specific node can be rewritten without affecting the rest of the tree.

**Steps:**
1.  **Setup:** Initialize `InteractiveRaptorEngine` with a pre-populated DB.
2.  **Action:** Select a node (e.g., ID "node_123"). Record its current text.
3.  **Action:** Call `engine.refine_node("node_123", "Translate to Japanese")`.
4.  **Verify:** The returned node has Japanese text.
5.  **Verify:** Fetch "node_123" from the DB again. The text is Japanese.
6.  **Verify:** The node's children indices are UNCHANGED. The tree structure is intact.

### Scenario 3.2: Concurrent Access (The "Stress Test")
**Priority:** High
**Goal:** Ensure the system doesn't crash when the GUI (read) and Engine (write) access the DB simultaneously.

**Steps:**
1.  **Setup:**
    -   Thread A: Continually reads random nodes from the DB.
    -   Thread B: Continually updates random nodes in the DB.
2.  **Action:** Run both threads for 30 seconds.
3.  **Verify:** No `sqlite3.OperationalError: database is locked` occurs.
4.  **Verify:** The process does not hang (deadlock).

### Scenario 3.3: History Tracking (The "Audit Trail")
**Priority:** Medium
**Goal:** Verify that user changes are logged.

**Steps:**
1.  **Setup:** Fetch a fresh node.
2.  **Action:** Refine it with instruction "Make shorter".
3.  **Action:** Refine it again with instruction "Make funnier".
4.  **Verify:** `node.metadata.refinement_history` should be a list containing `["Make shorter", "Make funnier"]`.
5.  **Verify:** `node.metadata.is_user_edited` is `True`.

## 2. Behavior Definitions (Gherkin)

### Feature: Interactive Refinement

```gherkin
Feature: Node Refinement
  As a user
  I want to rewrite a specific summary node
  So that I can tailor it to my understanding

  Scenario: User updates a node
    Given a summary node with ID "123"
    And the user provides instruction "Simplify this"
    When the interactive engine processes the request
    Then the node "123" text should be updated
    And the node ID should remain "123"
    And the children references should be preserved
    And the change should be persisted to the database

  Scenario: Refinement history is logged
    Given a node is refined
    When the update is saved
    Then the metadata should show is_user_edited = True
    And the instruction should be appended to refinement_history
```

### Feature: Thread Safety

```gherkin
Feature: Database Concurrency
  As a system
  I want to handle multiple read/write requests
  So that the GUI doesn't freeze or crash

  Scenario: Simultaneous Read/Write
    Given a background process is writing to the DB
    When the GUI tries to read a node
    Then the read should succeed (eventually)
    And no locking error should be raised
```
