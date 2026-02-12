# Cycle 02 User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios validate that the system correctly generates a DIKW hierarchy when the `--mode dikw` flag is used.

### Scenario 02-A: DIKW Mode Execution
**Priority:** Critical
**Description:** Verify that running the CLI with `--mode dikw` generates nodes with distinct `dikw_level` metadata.
**Procedure:**
1.  Prepare a test file `test_data/sample.txt` (approx. 5000 tokens).
2.  Run `matome run test_data/sample.txt --mode dikw`.
3.  Open the resulting `results/chunks.db`.
4.  Execute SQL queries:
    *   `SELECT count(*) FROM nodes WHERE metadata LIKE '%"dikw_level": "wisdom"%'`
    *   `SELECT count(*) FROM nodes WHERE metadata LIKE '%"dikw_level": "knowledge"%'`
    *   `SELECT count(*) FROM nodes WHERE metadata LIKE '%"dikw_level": "information"%'`
**Pass Criteria:**
*   Each query returns at least one record.
*   The total number of DIKW nodes matches the expected tree structure (e.g., 1 Wisdom, several Knowledge, many Information).

### Scenario 02-B: Content Quality Check (Manual)
**Priority:** High
**Description:** Verify that the content generated for each level matches the semantic definition.
**Procedure:**
1.  Inspect the text content of the Wisdom node.
2.  Inspect the text content of an Information node.
**Pass Criteria:**
*   **Wisdom:** Must be short (20-50 chars), abstract, and philosophical. (e.g., "True learning is the constant refinement of one's mental models.")
*   **Information:** Must contain actionable steps or a checklist. (e.g., "- Review quarterly reports. - Compare YOY growth.")

### Scenario 02-C: Default Mode Preservation
**Priority:** Medium
**Description:** Ensure that running without `--mode` (or with `--mode default`) still produces standard summaries.
**Procedure:**
1.  Run `matome run test_data/sample.txt`.
2.  Inspect the DB.
**Pass Criteria:**
*   Nodes have `dikw_level="data"` (or default).
*   Content looks like standard paragraph summaries, not aphorisms.

## 2. Behavior Definitions (Gherkin)

### Feature: DIKW Tree Generation

```gherkin
Feature: Semantic Zooming Generation
  As a user
  I want the system to organize information into Wisdom, Knowledge, and Information
  So that I can understand the content at different levels of abstraction

  Scenario: Generating a DIKW tree
    Given a text file "investment_guide.txt"
    When I run the command "matome run investment_guide.txt --mode dikw"
    Then the system should generate a root node with level "wisdom"
    And the system should generate intermediate nodes with level "knowledge"
    And the system should generate leaf summary nodes with level "information"
```
