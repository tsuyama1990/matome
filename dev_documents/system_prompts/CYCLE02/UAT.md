# Cycle 02: User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios verify the correctness of the **DIKW Generation Engine**.

### Scenario 1: Default Mode Execution (Regression)
**Priority**: High
**Goal**: Ensure that `matome run input.txt --mode default` (or no mode) still produces a standard summary tree.
- **Steps**:
  1. Run `matome run test_data/small.txt`.
  2. Verify output files (`summary_all.md`, `chunks.db`).
  3. Verify that `dikw_level` metadata is NOT set or defaults to a standard value (e.g., `None`).

### Scenario 2: DIKW Mode Execution
**Priority**: Critical
**Goal**: Ensure that `matome run input.txt --mode dikw` activates the new logic.
- **Steps**:
  1. Run `matome run test_data/small.txt --mode dikw`.
  2. Load the resulting `chunks.db`.
  3. Inspect the Root Node:
     - `metadata.dikw_level` MUST be `wisdom`.
     - `text` SHOULD be short (20-100 chars).
  4. Inspect Child Nodes (Intermediate):
     - `metadata.dikw_level` MUST be `knowledge`.
     - `text` SHOULD describe mechanisms/frameworks.
  5. Inspect Leaf Nodes (Initial Summaries):
     - `metadata.dikw_level` MUST be `information`.
     - `text` SHOULD be actionable.

### Scenario 3: Hierarchy Quality Verification
**Priority**: Medium
**Goal**: Manual check of the content quality.
- **Steps**:
  1. Read the generated `summary_dikw.md` (or inspect via `sqlite3`).
  2. Check if the "Wisdom" is truly abstract (e.g., "Persistence beats talent") vs specific (e.g., "John practiced 10 hours").
  3. Check if "Information" contains actionable verbs (e.g., "Do X", "Check Y").

## 2. Behavior Definitions (Gherkin)

### Feature: DIKW Tree Generation

**Scenario: Generating a DIKW Tree**
  GIVEN a text file with sufficient length (requires multiple levels)
  AND `ProcessingConfig` is set to `mode=DIKW`
  WHEN I execute the `RaptorEngine` pipeline
  THEN the resulting tree must have a root node of type `Wisdom`
  AND intermediate nodes of type `Knowledge`
  AND leaf summary nodes of type `Information`
  AND the `metadata.dikw_level` field must be populated for all nodes.

**Scenario: Strategy Application**
  GIVEN the engine is processing level 0 (chunks -> first summaries)
  WHEN the mode is `DIKW`
  THEN the `InformationStrategy` must be used.

**Scenario: Root Refinement**
  GIVEN the engine has finished building the tree
  WHEN the mode is `DIKW`
  THEN the engine must ensure the final root node represents `Wisdom`
  (either by summarizing the top `Knowledge` nodes or by refining the existing root).
