# Cycle 02: DIKW Generation Engine - User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios focus on validating the "Semantic Zooming" capability—that is, whether the system correctly generates different *types* of content at different levels.

### Scenario 2.1: The Wisdom Check (Root Level)
**Priority:** High
**Goal:** Verify that the highest-level summary is abstract and profound, not just a "summary of summaries".

**Steps:**
1.  **Setup:** Run the CLI `matome run test_data/sample.txt --mode dikw`.
2.  **Action:** Query the Root Node from `chunks.db` (the node with the highest level).
3.  **Verify (Manual):** The text should be short (approx. 50 words or less) and written in a conceptual/philosophical tone.
4.  **Verify (Automated - Optional):** Check if `metadata['dikw_level'] == 'wisdom'`.

### Scenario 2.2: The Action Check (Leaf/Twig Level)
**Priority:** High
**Goal:** Verify that lower-level summaries are actionable.

**Steps:**
1.  **Setup:** Use the same `chunks.db`.
2.  **Action:** Query nodes at `tree_level=1` (directly above chunks).
3.  **Verify (Manual):** The text should look like a checklist or set of instructions. It should contain specific nouns/verbs from the source text.
4.  **Verify (Automated):** Check if `metadata['dikw_level'] == 'information'` (or 'action').

### Scenario 2.3: Hierarchy Consistency
**Priority:** Medium
**Goal:** Ensure the tree structure logically flows from Wisdom -> Knowledge -> Action.

**Steps:**
1.  **Setup:** Load the tree in a notebook.
2.  **Action:** Traverse from Root -> Child -> Grandchild.
3.  **Verify:**
    -   Root (Wisdom): "Invest for the long term."
    -   Child (Knowledge): "Long-term investing works because of compound interest."
    -   Grandchild (Action): "- Open a brokerage account.\n- Buy index funds."
    -   *If the grandchild is more abstract than the child, the test fails.*

## 2. Behavior Definitions (Gherkin)

### Feature: DIKW Strategy Selection

```gherkin
Feature: Semantic Zooming Strategies
  As a user
  I want summaries to change in nature as I zoom in/out
  So that I can understand the "Why" (Wisdom) and the "How" (Action) separately

  Scenario: Root Level Generation (Wisdom)
    Given the Raptor Engine is processing the root level (Level 3+)
    When it requests a summary
    Then it should use the WisdomStrategy
    And the generated text should be labeled as "wisdom" in metadata

  Scenario: Intermediate Level Generation (Knowledge)
    Given the Raptor Engine is processing an intermediate level (Level 2)
    When it requests a summary
    Then it should use the KnowledgeStrategy
    And the generated text should be labeled as "knowledge" in metadata

  Scenario: Low Level Generation (Action)
    Given the Raptor Engine is processing the first level above chunks (Level 1)
    When it requests a summary
    Then it should use the ActionStrategy
    And the generated text should be labeled as "information" in metadata
```
