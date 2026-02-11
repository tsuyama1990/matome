# Cycle 02 User Acceptance Test (UAT): DIKW Generation Engine

## 1. Test Scenarios

### Scenario ID: C02-01 (DIKW Output Quality)
**Priority**: High
**Objective**: Qualitatively verify that the generated content for each level matches the "Semantic Zooming" intent.
**Description**:
As a user (or QA), I want to see that the "Wisdom" is actually philosophical and short, and the "Action" is actually a checklist.
**Steps**:
1.  Create `tests/uat/C02_quality_check.ipynb`.
2.  **Ingest**: Load a sample text known to contain actionable advice (e.g., the provided "Emin's Strategy" text).
3.  **Run**: Execute the engine with `--mode dikw`.
4.  **Inspect Wisdom**: Print the text of the Root Node.
    -   *Pass Criteria*: It is < 100 characters. It sounds like a motto. It does NOT contain specific numbers or dates.
5.  **Inspect Action**: Print the text of a Leaf Node.
    -   *Pass Criteria*: It contains markdown checkboxes `[ ]` or bullet points. It contains specific entities (e.g., "PSR < 1.0").

### Scenario ID: C02-02 (Mode Switching)
**Priority**: Medium
**Objective**: Verify that the system can still run in "Default" mode and that "DIKW" mode is distinctly different.
**Description**:
As a legacy user, I want to ensure my existing workflow (summaries, not checklists) still works.
**Steps**:
1.  Run `matome run sample.txt --mode default`.
2.  Inspect output. Nodes should be standard summaries. Metadata `dikw_level` should be `DATA` (default).
3.  Run `matome run sample.txt --mode dikw`.
4.  Inspect output. Nodes should be specialized. Metadata `dikw_level` should vary (WISDOM, KNOWLEDGE, INFORMATION).

## 2. Behavior Definitions (Gherkin)

### Feature: DIKW Strategy Selection

**Scenario**: Generating the Root Node
  **GIVEN** the RAPTOR engine has finished processing all child clusters
  **AND** only one cluster remains (the Root)
  **WHEN** the engine generates the summary for this cluster
  **THEN** it should use the `WisdomStrategy`
  **AND** the resulting `SummaryNode` should have `metadata.dikw_level` set to `WISDOM`

**Scenario**: Generating Leaf Summaries
  **GIVEN** the RAPTOR engine is processing Level 0 clusters (chunks)
  **WHEN** the engine generates summaries
  **THEN** it should use the `ActionStrategy`
  **AND** the resulting `SummaryNode` should have `metadata.dikw_level` set to `INFORMATION` (or `ACTION`)

**Scenario**: Generating Intermediate Summaries
  **GIVEN** the RAPTOR engine is processing Level 1 to Max-1
  **WHEN** the engine generates summaries
  **THEN** it should use the `KnowledgeStrategy`
  **AND** the resulting `SummaryNode` should have `metadata.dikw_level` set to `KNOWLEDGE`
