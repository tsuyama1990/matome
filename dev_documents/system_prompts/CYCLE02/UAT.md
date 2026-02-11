# Cycle 02: User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario A: Verify DIKW Generation (Semantic Zooming)
*   **ID**: S02-01
*   **Priority**: High
*   **Description**: Run the CLI in DIKW mode and verify that the output structure respects the hierarchy (Wisdom -> Knowledge -> Information -> Data).
*   **Preconditions**:
    *   System built with `PromptStrategy` and `DIKW` mode support.
    *   `test_data/sample.txt` exists (long enough to generate 3+ levels).
*   **Steps**:
    1.  Run `uv run matome run test_data/sample.txt --mode dikw`.
    2.  Check `summary_dikw.md` (or inspect `chunks.db`).
    3.  Find the root node (Level 1 / Wisdom).
        *   **Check**: Is the text short (20-50 chars)?
        *   **Check**: Does it look like a "philosophy" or "truth"?
    4.  Find its children (Level 2 / Knowledge).
        *   **Check**: Does it explain "Why" or mechanisms?
    5.  Find its children (Level 3 / Information).
        *   **Check**: Does it contain actionable items (checklists)?
    6.  Find leaves (Level 4 / Data).
        *   **Check**: Are they original text chunks?

### Scenario B: Verify Default Mode Remains Unchanged
*   **ID**: S02-02
*   **Priority**: Medium
*   **Description**: Ensure that running without `--mode dikw` (default) still produces standard RAPTOR summaries.
*   **Preconditions**: Same as above.
*   **Steps**:
    1.  Run `uv run matome run test_data/sample.txt`.
    2.  Check `summary_all.md`.
    3.  Verify the content is a standard hierarchical summary, not force-compressed into aphorisms.

## 2. Behavior Definitions (Gherkin)

### Feature: DIKW Mode Processing

**Scenario: Generating Wisdom Layer**
  **GIVEN** the processing mode is `DIKW`
  **AND** the RAPTOR engine is processing the final root level
  **WHEN** the summarizer is invoked
  **THEN** it should use `WisdomStrategy`
  **AND** the output text should be between 20 and 50 characters

**Scenario: Generating Information Layer**
  **GIVEN** the processing mode is `DIKW`
  **AND** the RAPTOR engine is processing the first level of clusters (closest to data)
  **WHEN** the summarizer is invoked
  **THEN** it should use `ActionStrategy`
  **AND** the output text should contain bullet points or checklists

**Scenario: Generating Knowledge Layer**
  **GIVEN** the processing mode is `DIKW`
  **AND** the RAPTOR engine is processing intermediate levels
  **WHEN** the summarizer is invoked
  **THEN** it should use `KnowledgeStrategy`
