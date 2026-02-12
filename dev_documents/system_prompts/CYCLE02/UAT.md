# Cycle 02 User Acceptance Testing (UAT)

## 1. Test Scenarios

Cycle 02 implements the specific summarization logic for Semantic Zooming. The UAT focuses on verifying that each level produces distinct and appropriate content.

### Scenario CYCLE02-01: Wisdom Generation (Root)
**Priority:** High
**Description:** Verify that the `WisdomStrategy` produces a single, profound sentence.
**Steps:**
1.  **Preparation:** Use `test_data/sample.txt` (a philosophical or business text).
2.  **Execution:** Run `uv run matome run test_data/sample.txt --mode wisdom`.
3.  **Verification:** Check the output summary.
4.  **Result Check:** The text should be between 20-50 characters, abstract, and profound (e.g., "Change is inevitable."). It should not contain specific dates or names.

### Scenario CYCLE02-02: Knowledge Extraction (Branches)
**Priority:** Medium
**Description:** Verify that `KnowledgeStrategy` extracts underlying mechanisms.
**Steps:**
1.  **Preparation:** Use the same text.
2.  **Execution:** Run `uv run matome run test_data/sample.txt --mode knowledge`.
3.  **Verification:** Check for explanations of "Why" and "How".
4.  **Result Check:** Output should contain structured concepts or mental models.

### Scenario CYCLE02-03: Actionable Information (Leaves)
**Priority:** Medium
**Description:** Verify that `InformationStrategy` produces actionable steps.
**Steps:**
1.  **Preparation:** Use the same text.
2.  **Execution:** Run `uv run matome run test_data/sample.txt --mode information`.
3.  **Verification:** Check for bullet points or checklists.
4.  **Result Check:** Output should contain verb-first instructions (e.g., "- Review the quarterly report").

**Jupyter Notebook:** `tutorials/CYCLE02_DIKW_Modes.ipynb`

## 2. Behavior Definitions

### Feature: DIKW Strategy Selection

**Scenario:** Wisdom Generation
    **Given** a text "The stock market fluctuates based on human emotion and algorithmic trading..."
    **When** processed with `WisdomStrategy`
    **Then** the output should be concise (approx 30 chars)
    **And** the metadata `dikw_level` should be "wisdom"

**Scenario:** Action Checklist Generation
    **Given** a text describing a process
    **When** processed with `InformationStrategy`
    **Then** the output should be a markdown list
    **And** the metadata `dikw_level` should be "information"

**Scenario:** Unknown Mode
    **Given** the CLI command `matome run ... --mode alien`
    **When** executed
    **Then** it should display a helpful error listing valid modes (wisdom, knowledge, information, data).
