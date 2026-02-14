# Cycle 01 UAT: DIKW Generation Verification

## 1. Test Scenarios

### Scenario ID: UAT-C01-01 - Wisdom Generation (L1)
**Priority:** High
**Description:**
The system must generate a profound, concise "Wisdom" statement as the root of the tree. This tests the `WisdomStrategy` and its integration with the `RaptorEngine`.
**Steps:**
1.  Prepare a sample text file (`test_data/input_text.txt`) with roughly 2000 words (e.g., an essay or article).
2.  Run the CLI command: `uv run matome run test_data/input_text.txt --mode dikw`.
3.  Check the output summary file (`results/summary_dikw.md` or similar).
4.  Verify the content of the top-level summary (Root Node).
**Expected Result:**
The root summary should be short (under 50 words) and philosophical. It should capture the "essence" or "moral" of the text, not just a summary of points.
**Marimo Validation:**
Create a Marimo notebook `tutorials/UAT_AND_TUTORIAL.py` that loads the generated `chunks.db` and displays the Root Node text.

### Scenario ID: UAT-C01-02 - Information Generation (L3)
**Priority:** High
**Description:**
The system must generate actionable "Information" nodes at the bottom level (summarizing chunks). This tests the `InformationStrategy`.
**Steps:**
1.  Run the CLI command as above.
2.  Inspect the generated `chunks.db` using the Marimo notebook.
3.  Retrieve a node from Level 1 (the lowest summary level).
4.  Read its text.
**Expected Result:**
The text should be formatted as a checklist or a "How-To" guide. It should contain specific actions, steps, or rules derived from the source text. It should *not* be abstract philosophy.

### Scenario ID: UAT-C01-03 - Metadata Verification
**Priority:** Medium
**Description:**
Verify that the `metadata` field is correctly populated with `dikw_level`.
**Steps:**
1.  Run the CLI command as above.
2.  Open the `chunks.db` using `sqlite3` or the Marimo notebook.
3.  Query the `summary_nodes` table.
4.  Check the `metadata` column for JSON values.
**Expected Result:**
-   The Root Node must have `{"dikw_level": "wisdom"}`.
-   Intermediate Nodes must have `{"dikw_level": "knowledge"}`.
-   Leaf Summary Nodes must have `{"dikw_level": "information"}`.
-   Leaf Chunks (if present in the summary table, though they usually aren't) or their representation must correspond to `Data`.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: DIKW Tree Generation

  Scenario: Generate Wisdom Node
    Given a text file "input.txt" with content about "Investment Philosophy"
    When I run "matome run input.txt --mode dikw"
    Then the system should generate a Root Summary Node
    And the Root Node metadata should contain "dikw_level": "wisdom"
    And the Root Node text length should be less than 300 characters
    And the Root Node text should resemble a philosophical statement

  Scenario: Generate Actionable Information
    Given the generated DIKW tree from "input.txt"
    When I inspect a Level 1 Summary Node (bottom summary layer)
    Then the Node metadata should contain "dikw_level": "information"
    And the Node text should contain a Markdown checklist ("- [ ]")
    And the Node text should describe specific actions or steps

  Scenario: Verify Hierarchy Integrity
    Given the generated DIKW tree
    When I traverse from Root to Leaf
    Then the traversal order should be Wisdom -> Knowledge -> Information -> Data
    And each parent node should summarize its children according to its level strategy
```
