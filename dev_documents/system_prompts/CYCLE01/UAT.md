# Cycle 01 User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario 01-A: Regression Test - CLI Summarization Consistency
**Priority:** High
**Goal:** Verify that the core refactoring of `SummarizationAgent` and `SummaryNode` has not broken the existing CLI functionality. The system must still produce a valid `chunks.db` and output files from a raw text input.

**Description:**
The primary user interaction for Matome in its current state is the Command Line Interface (CLI). In this cycle, we have significantly altered the internal plumbing of the `SummarizationAgent` (by introducing the `PromptStrategy` pattern) and the data schema of `SummaryNode` (by making `metadata` a strict Pydantic model). A failure here would mean the refactoring was destructive.

This scenario mimics a standard user workflow: taking a raw text file and running the default `matome run` command. The user expects the process to complete without errors, and the resulting `summary.md` to be identical (or semantically equivalent) to the previous version.

**Execution Steps (Manual or Scripted):**
1.  **Preparation:**
    *   Ensure the environment is clean (no existing `results/` directory).
    *   Use a known input file: `test_data/sample.txt` (approx. 2000 tokens).
    *   Set `OPENAI_API_KEY` (or use Mock Mode if implemented, but preferably Real Mode for regression).
2.  **Action:**
    *   Run command: `python -m matome.cli run test_data/sample.txt`
3.  **Observation:**
    *   Check standard output (logs). It should show "Processed X chunks", "Clustering...", "Summarizing Level 1...".
    *   Verify exit code is 0.
4.  **Verification:**
    *   Inspect `results/chunks.db`. Use a SQLite viewer or Python script.
    *   Query: `SELECT count(*) FROM nodes WHERE type='summary'`. Should be > 0.
    *   Inspect `results/summary.md`. It should contain the markdown summary.

**Success Criteria:**
*   The CLI command completes successfully.
*   The `chunks.db` file is created and populated.
*   The summaries in the DB are coherent text (not empty, not error messages).
*   No `ValidationError` regarding `SummaryNode` metadata is raised in the logs.

### Scenario 01-B: Metadata Capability Verification
**Priority:** Medium
**Goal:** Confirm that the new `NodeMetadata` schema is correctly enforced and persisted. This ensures the foundation for DIKW is solid.

**Description:**
While the CLI doesn't yet *use* the DIKW levels to generate different content (that's Cycle 02), the *capability* to store this information must be proven now. This scenario involves a "Developer User" (or a test script acting as one) manually interacting with the `DiskChunkStore` to verify that the new metadata fields (`dikw_level`, `is_user_edited`) are operational.

We want to ensure that if we save a node with `dikw_level='wisdom'`, it stays `'wisdom'` after a round-trip to the SQLite database. If we try to save `dikw_level='invalid_level'`, it should raise a validation error, protecting the integrity of our future logic.

**Execution Steps (Jupyter Notebook or Python Script):**
1.  **Setup:**
    *   Initialize a `DiskChunkStore` (temporary or file-based).
    *   Import `SummaryNode`, `NodeMetadata`, `DIKWLevel`.
2.  **Valid Insertion:**
    *   Create `NodeMetadata(dikw_level=DIKWLevel.WISDOM, is_user_edited=True)`.
    *   Create a `SummaryNode` using this metadata.
    *   Add to Store: `store.add_summary(node)`.
3.  **Retrieval:**
    *   Fetch the node: `retrieved = store.get_node(node.id)`.
    *   **Check:** `retrieved.metadata.dikw_level` should be `DIKWLevel.WISDOM`.
    *   **Check:** `retrieved.metadata.is_user_edited` should be `True`.
4.  **Invalid Insertion (Negative Test):**
    *   Attempt to create `NodeMetadata(dikw_level="super_wisdom")`.
    *   **Expectation:** `pydantic.ValidationError` should be raised immediately.

**Success Criteria:**
*   Round-trip persistence of `dikw_level` works correctly.
*   Pydantic validation prevents invalid enum values.
*   The default values (None for `dikw_level`, False for `is_user_edited`) are applied if not specified.

## 2. Behavior Definitions (Gherkin)

The following Gherkin scenarios define the expected behavior of the system after Cycle 01 implementation. These serve as the "contract" for the acceptance tests.

### Feature: Prompt Strategy Integration

**Background:**
  Given the `SummarizationAgent` is initialized
  And the default `BaseSummaryStrategy` is used

**Scenario: Default Summarization Behavior**
  Given a text chunk "The quick brown fox jumps over the lazy dog."
  When I call `agent.summarize(text)`
  Then the `BaseSummaryStrategy.generate_prompt` method should be invoked
  And the generated prompt should contain the text
  And the prompt should match the format of `COD_TEMPLATE`
  And the agent should return a string summary

**Scenario: Strategy Injection**
  Given I have a custom `MockStrategy`
  And the `MockStrategy.generate_prompt` returns "MOCKED PROMPT"
  When I initialize `SummarizationAgent` with this strategy
  And I call `agent.summarize("input text")`
  Then the LLM should receive "MOCKED PROMPT" as input
  And the response parsing should use `MockStrategy.parse_response`

### Feature: Enhanced Node Metadata

**Scenario: Storing Wisdom Nodes**
  Given a `DiskChunkStore` connected to a database
  And a `SummaryNode` with `dikw_level` set to "wisdom"
  When I add the node to the store
  And I retrieve the node by its ID
  Then the retrieved node's metadata should have `dikw_level` equal to "wisdom"
  And `is_user_edited` should be false (default)

**Scenario: Storing User-Edited Knowledge Nodes**
  Given a `DiskChunkStore` connected to a database
  And a `SummaryNode` with `dikw_level` set to "knowledge"
  And `is_user_edited` set to true
  When I add the node to the store
  And I retrieve the node by its ID
  Then the retrieved node's metadata should have `dikw_level` equal to "knowledge"
  And `is_user_edited` should be true

**Scenario: Backward Compatibility with Legacy Metadata**
  Given a `DiskChunkStore` containing legacy nodes (created before Cycle 01)
  And a legacy node has metadata `{"cluster_id": 123}` but no `dikw_level`
  When I retrieve this node using the new `SummaryNode` model
  Then the node should be loaded successfully
  And the `dikw_level` should be null
  And the `cluster_id` should be preserved (due to `extra="allow"`)
