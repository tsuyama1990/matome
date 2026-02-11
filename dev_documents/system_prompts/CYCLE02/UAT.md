# Cycle 02 User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario 02-A: DIKW Hierarchy Generation
**Priority:** Critical
**Goal:** Verify that the `RaptorEngine` correctly applies different prompt strategies at different levels of the tree, resulting in a distinct Wisdom-Knowledge-Information structure.

**Description:**
This is the core functional requirement of Cycle 02. The user expects that when they process a document, the resulting summary tree is not just a hierarchy of shorter texts, but a hierarchy of *meaning*. The root node should be a philosophical "Wisdom" statement, the intermediate nodes should be structural "Knowledge" explanations, and the leaf summaries should be actionable "Information" checklists.

**Execution Steps (Scripted):**
1.  **Preparation:**
    *   Clean environment.
    *   Input file: `test_data/agile_manifesto.txt` (or similar procedural text).
    *   Configuration: Ensure `RAPTOR` is enabled.
2.  **Action:**
    *   Run `matome run test_data/agile_manifesto.txt`.
3.  **Verification:**
    *   Load `results/chunks.db`.
    *   **Root Check:** Get the root node.
        *   Assert `metadata.dikw_level == "wisdom"`.
        *   Assert `len(text) < 200` (Wisdom should be concise).
        *   Assert text style (qualitative): Does it sound like an aphorism? (e.g., "Agile values individuals over processes.")
    *   **Level 1 Check:** Get nodes with `level=1`.
        *   Assert `metadata.dikw_level == "information"`.
        *   Assert text contains markdown checklist items (`- [ ]`) or bullet points.
    *   **Level 2 Check (if applicable):** Get nodes with `level=2`.
        *   Assert `metadata.dikw_level == "knowledge"`.
        *   Assert text structure is explanatory paragraphs.

**Success Criteria:**
*   The tree is built successfully.
*   Metadata `dikw_level` is correctly assigned for each level.
*   Content style matches the level definition (Wisdom = Short, Info = Checklist).

### Scenario 02-B: Single Node Strategy Override
**Priority:** High
**Goal:** Verify that the `SummarizationAgent` can accept a specific strategy override, which is crucial for the future "Interactive Refinement" feature (where a user might want to re-summarize a specific node with a different intent).

**Description:**
In Cycle 03, we will let users say "Rewrite this as a checklist". To support this, the underlying agent must support swapping the strategy on the fly for a single call. This scenario tests that capability in isolation.

**Execution Steps (Python Script):**
1.  **Setup:**
    *   Instantiate `SummarizationAgent`.
    *   Create a text sample: "To bake a cake, mix flour and eggs. Bake at 350F for 30 mins."
2.  **Action Strategy Test:**
    *   Call `agent.summarize(text, strategy=ActionStrategy())`.
    *   **Check:** Output should contain "- [ ] Mix flour and eggs" or similar.
3.  **Wisdom Strategy Test:**
    *   Call `agent.summarize(text, strategy=WisdomStrategy())`.
    *   **Check:** Output should be a single sentence like "Baking requires precision and patience." (or similar abstract summary).
4.  **Knowledge Strategy Test:**
    *   Call `agent.summarize(text, strategy=KnowledgeStrategy())`.
    *   **Check:** Output should explain the process structure.

**Success Criteria:**
*   The agent returns different outputs for the same input when different strategies are used.
*   The output format aligns with the strategy's goal.

## 2. Behavior Definitions (Gherkin)

### Feature: Level-Based Summarization Strategy

**Background:**
  Given the `RaptorEngine` is processing a document
  And the document has sufficient length to generate multiple levels

**Scenario: Generating Information Level (Level 1)**
  When the engine summarizes a cluster of Level 0 chunks (Data)
  Then it should use the `ActionStrategy`
  And the resulting summary node should have `metadata.dikw_level` set to "information"
  And the text content should be formatted as a checklist or actionable steps

**Scenario: Generating Knowledge Level (Intermediate)**
  When the engine summarizes a cluster of Level 1 nodes (Information)
  Then it should use the `KnowledgeStrategy`
  And the resulting summary node should have `metadata.dikw_level` set to "knowledge"
  And the text content should explain the structural relationships between the information nodes

**Scenario: Generating Wisdom Root (Final)**
  When the engine identifies the final root node
  Then it should re-summarize the root content using the `WisdomStrategy`
  And the resulting root node should have `metadata.dikw_level` set to "wisdom"
  And the text content should be a concise aphorism or guiding principle

### Feature: Manual Strategy Override

**Scenario: User Requests Checklists**
  Given a `SummarizationAgent` instance
  And a text input describing a process
  When I invoke `summarize` with `strategy=ActionStrategy`
  Then the output should be a markdown list
  And the output should strictly follow the checklist format
