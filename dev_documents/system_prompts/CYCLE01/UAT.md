# Cycle 01 User Acceptance Testing (UAT)

## 1. Test Scenarios

The goal of Cycle 01 is refactoring for future extensibility without breaking current functionality. Therefore, the UAT is primarily a **regression test**.

### Scenario CYCLE01-01: Regression Test (Base Functionality)
**Priority:** High
**Description:** Verify that the system still produces valid summaries using the default strategy after refactoring.
**Steps:**
1.  **Preparation:** Ensure `chunks.db` is empty or deleted.
2.  **Execution:** Run the CLI command: `uv run matome run test_data/sample.txt` (using a small sample file).
3.  **Verification:** Check that the process completes without errors.
4.  **Result Check:** Inspect the output (or `chunks.db`) to confirm summaries are generated and stored.

**Jupyter Notebook:** `tutorials/CYCLE01_Regression.ipynb` (Optional but recommended for quick verification).

## 2. Behavior Definitions

### Feature: Extensible Summarization Strategy

**Scenario:** Default Summarization (Base Strategy)
    **Given** a text file containing "The quick brown fox jumps over the lazy dog."
    **And** a `SummarizationAgent` initialized with `BaseSummaryStrategy`
    **When** the agent processes the text
    **Then** it should return a dictionary with a key "summary"
    **And** the summary should be a concise version of the input text
    **And** no "metadata" or "dikw_level" fields should be required for this base implementation (backward compatibility).

**Scenario:** Invalid Strategy
    **Given** a `SummarizationAgent`
    **When** initialized without a valid `PromptStrategy`
    **Then** it should raise a `TypeError` or `ValueError` (enforced by type hinting or runtime check).
