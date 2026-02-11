# Cycle 02: DIKW Generation Engine - User Acceptance Test (UAT)

## 1. Test Scenarios

### Scenario 2.1: Semantic Zooming Verification
**Objective**: Ensure that the system, when run in DIKW mode, produces summaries at distinct levels of abstraction (Wisdom, Knowledge, Action).
*   **Description**: Run the CLI with the `--mode dikw` flag on a sample text (e.g., `test_data/エミン流「会社四季報」最強の読み方.txt`). Inspect the resulting Markdown output or JSON structure.
*   **Success Criteria**:
    *   **Level 0 (Action)**: The leaf nodes contain clear checklists (e.g., `- [ ] ...`) and actionable instructions. They are detailed.
    *   **Level 1 (Knowledge)**: The intermediate nodes explain *why* the actions matter. They define frameworks or concepts.
    *   **Root (Wisdom)**: The top-level summary is concise (< 50 words), abstract, and philosophical. It captures the "soul" of the document.

### Scenario 2.2: Mixed Mode Handling
**Objective**: Verify that `DEFAULT` mode still works correctly and `DIKW` mode is opt-in.
*   **Description**: Run the CLI without the `--mode` flag (or with `--mode default`).
*   **Success Criteria**:
    *   The output is a standard "Chain of Density" summary.
    *   No checklist markers (unless present in source) or enforced brevity.
    *   This ensures backward compatibility for users who just want a summary.

### Scenario 2.3: Configuration Persistence
**Objective**: Verify that the processing mode is stored in the metadata or config log for reproducibility.
*   **Description**: Check the `run_config.json` (if implemented) or the `metadata` of generated nodes.
*   **Success Criteria**:
    *   Generated nodes clearly indicate their `dikw_level` in metadata.
    *   One can programmatically filter nodes by `dikw_level` (e.g., `store.get_nodes(level="wisdom")`).

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: DIKW Generation Mode

  Scenario: Generating Actionable Leaves (Level 0)
    GIVEN the processing mode is set to DIKW
    WHEN the RaptorEngine processes the base text chunks (Level 0)
    THEN it should use the ActionStrategy
    AND the resulting summaries should contain bullet points or checklists
    AND the node metadata should have dikw_level="information"

  Scenario: Generating Knowledge Branches (Level 1)
    GIVEN the processing mode is set to DIKW
    WHEN the RaptorEngine processes the Level 0 summaries (Level 1)
    THEN it should use the KnowledgeStrategy
    AND the resulting summaries should explain concepts and frameworks
    AND the node metadata should have dikw_level="knowledge"

  Scenario: Generating Wisdom Root (Level N)
    GIVEN the processing mode is set to DIKW
    WHEN the RaptorEngine processes the final level (Root)
    THEN it should use the WisdomStrategy
    AND the resulting summary should be short (< 50 words) and abstract
    AND the node metadata should have dikw_level="wisdom"
```
