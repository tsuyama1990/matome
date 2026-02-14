# Cycle 02 UAT: Interactive Engine Verification

## 1. Test Scenarios

### Scenario ID: UAT-C02-01 - Single Node Refinement
**Priority:** High
**Description:**
Verify that the `InteractiveRaptorEngine` can successfully update a single node's text and metadata based on a user instruction.
**Steps:**
1.  Initialize `DiskChunkStore` with a sample SummaryNode (L1 Wisdom).
2.  Text: "Initial wisdom text."
3.  Metadata: `{"dikw_level": "wisdom", "is_user_edited": false}`.
4.  Call `engine.refine_node(node_id, instruction="Make it more concise")`.
5.  Retrieve the node again from the store.
**Expected Result:**
-   Text should change (assuming mock LLM returns new text).
-   `metadata.is_user_edited` must be `true`.
-   `metadata.refinement_history` must contain `["Make it more concise"]`.

### Scenario ID: UAT-C02-02 - Concurrency & Persistence
**Priority:** Medium
**Description:**
Verify that the database supports concurrent read/write operations (simulating GUI usage) without locking errors.
**Steps:**
1.  Run a script that continuously reads a node in a loop (Reader Thread).
2.  Run another script that updates the same node in a loop (Writer Thread).
3.  Let them run for 5 seconds.
**Expected Result:**
-   No `sqlite3.OperationalError: database is locked` should occur.
-   The reader thread should eventually see updated values.
-   The database file (`chunks.db`) should remain valid.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Interactive Refinement

  Scenario: User Refines a Node
    Given a SummaryNode "N1" with text "Too long..."
    When I call refine_node("N1", "Shorten this")
    Then the system should generate a new summary based on "Shorten this"
    And the node "N1" in the database should be updated with the new text
    And the node "N1" metadata should have "is_user_edited" as true
    And the node "N1" metadata should include "Shorten this" in history

  Scenario: Database Concurrency
    Given a running reader process on "chunks.db"
    When I perform a write operation on "chunks.db" via the Interactive Engine
    Then the write should succeed without locking the database
    And the reader should be able to read the new data
```
