# Cycle 02: DIKW Generation Engine - User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario ID: C02-01 - Wisdom Generation (L1)
**Priority:** High
**Goal:** Verify that the system generates a distinct "Wisdom" node at the root.
**Description:** Run the CLI with `--mode dikw` on a philosophical text (e.g., "Emin Yurumazu" sample) and check if the root node is a short, profound one-liner.
**Prerequisites:**
-   Sample text (`test_data/sample.txt`).
-   `OPENAI_API_KEY` set.
-   `chunks.db` (newly created).

### Scenario ID: C02-02 - Action Extraction (L3)
**Priority:** Medium
**Goal:** Verify that lower-level summaries are actionable.
**Description:** Run the CLI with `--mode dikw`. Inspect the leaf summary nodes (Level 1 above chunks).
**Prerequisites:** Same as above.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: DIKW Generation

  Scenario: Generate Wisdom Root
    GIVEN a text file "philosophy.txt"
    WHEN I run "matome run philosophy.txt --mode dikw"
    THEN the generated root node should have metadata "dikw_level": "wisdom"
    AND the root node text should be less than 100 characters
    AND the root node text should not contain bullet points

  Scenario: Generate Action Checklists
    GIVEN a text file with instructions
    WHEN I run "matome run instructions.txt --mode dikw"
    THEN the leaf summary nodes should have metadata "dikw_level": "action"
    AND the text should contain checklist items like "- [ ]"
```
