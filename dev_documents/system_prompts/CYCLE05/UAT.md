# Cycle 05 User Acceptance Testing (UAT) Plan

## 1. Test Scenarios

### Scenario 14: Canvas File Generation (Priority: High)
*   **Goal**: Ensure the exported `.canvas` file is valid JSON and importable by Obsidian.
*   **Inputs**: A populated `DocumentTree`.
*   **Expected Outcome**: A JSON file with `nodes` and `edges` keys. Node coordinates should be spread out, not all at (0,0).

### Scenario 15: Visual Hierarchy Check (Priority: Medium)
*   **Goal**: Ensure the visual layout reflects the logical structure.
*   **Inputs**: A tree with Root -> [A, B] -> [a1, a2, b1].
*   **Expected Outcome**:
    *   Root is at the top.
    *   A and B are below Root.
    *   a1, a2 are below A; b1 is below B.
    *   Lines connect Root -> A, A -> a1, etc.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Obsidian Canvas Export

  Scenario: Exporting a DocumentTree
    GIVEN a DocumentTree with multiple levels
    WHEN the ObsidianCanvasExporter is called
    THEN it should generate a JSON file
    AND the file should contain nodes for each summary and chunk
    AND the nodes should be connected by edges representing parent-child relationships
    AND the layout should position children below their parents
```
