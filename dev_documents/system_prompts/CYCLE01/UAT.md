# Cycle 01: Core Logic Refactoring & DIKW Metadata - User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario ID: C01-01 - Regression Testing (CLI Functionality)
**Priority:** High
**Goal:** Ensure that the existing CLI functionality is not broken by the refactoring.
**Description:** Run the standard `matome run` command on a sample text file and verify that it still produces a `chunks.db` and output summary, even though the internal logic has changed to use `PromptStrategy`.
**Prerequisites:**
-   A sample text file (e.g., `tests/data/sample.txt`).
-   `OPENAI_API_KEY` set (or mock environment).

### Scenario ID: C01-02 - Metadata Structure Verification
**Priority:** Medium
**Goal:** Verify that the system *can* store the new DIKW metadata fields, even if it doesn't populate them yet.
**Description:** Use a Python script to manually create a `SummaryNode` with `dikw_level="wisdom"` in its metadata and save/load it from the `DiskChunkStore`.
**Prerequisites:** None (runs in python shell).

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Prompt Strategy Refactoring

  Scenario: Run CLI with Legacy Strategy (Default)
    GIVEN the application is installed
    AND a valid input file "sample.txt" exists
    WHEN I run the command "matome run sample.txt"
    THEN the process should complete successfully
    AND a "chunks.db" file should be created
    AND the output summary should not be empty

  Scenario: Metadata Compatibility
    GIVEN a DiskChunkStore instance
    WHEN I save a SummaryNode with metadata {"dikw_level": "wisdom"}
    THEN I should be able to retrieve the node
    AND the retrieved node's metadata should contain "dikw_level": "wisdom"
```
