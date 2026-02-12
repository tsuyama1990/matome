# Cycle 01 User Acceptance Testing (UAT)

## 1. Test Scenarios

Since Cycle 01 is focused on internal refactoring, the "User Acceptance" primarily concerns the developer experience and system stability. The user-visible behavior (summarization) must remain unchanged.

### Scenario 01-A: Strategy Injection Verification
**Priority:** Critical
**Description:** Verify that the `SummarizationAgent` correctly utilizes an injected `PromptStrategy` instead of its hardcoded logic.
**Procedure:**
1.  Create a custom `MockStrategy` that always returns "MOCK_PROMPT" for format_prompt and `{"summary": "MOCK_RESULT"}` for parse_output.
2.  Instantiate `SummarizationAgent` with this strategy.
3.  Call `agent.summarize("test text")`.
4.  Assert that the returned summary is exactly "MOCK_RESULT".
**Pass Criteria:** The agent returns the mock result, proving the strategy pattern is active.

### Scenario 01-B: Schema Backward Compatibility
**Priority:** High
**Description:** Ensure that old data (without DIKW fields) can be loaded into the new `NodeMetadata` schema without errors.
**Procedure:**
1.  Create a dictionary representing an old node: `{"cluster_id": 1, "summary": "Old summary"}`.
2.  Attempt to instantiate `NodeMetadata(**old_dict)`.
3.  Inspect the created object.
**Pass Criteria:**
*   Instantiation succeeds (no Validation Error).
*   `dikw_level` is `DIKWLevel.DATA`.
*   `is_user_edited` is `False`.
*   `refinement_history` is `[]`.

### Scenario 01-C: Regression Testing (Existing Pipeline)
**Priority:** Critical
**Description:** Verify that the full existing pipeline still works with the default configuration.
**Procedure:**
1.  Run the standard `matome run <test_file>` command on a small test file.
2.  Check the output database.
**Pass Criteria:**
*   The command completes successfully (exit code 0).
*   The database contains valid summary nodes.
*   The summaries look reasonable (not empty or garbage).

## 2. Behavior Definitions (Gherkin)

### Feature: Prompt Strategy Integration

```gherkin
Feature: Dynamic Prompt Strategy
  As a developer
  I want to inject custom prompt strategies into the summarizer
  So that I can change the behavior without modifying the agent class

  Scenario: Using a custom strategy
    Given a SummarizationAgent initialized with a "MockStrategy"
    When I call summarize with the text "Hello World"
    Then the agent should call "MockStrategy.format_prompt" with "Hello World"
    And the agent should return the result from "MockStrategy.parse_output"
```

### Feature: Node Metadata Migration

```gherkin
Feature: Metadata Schema Evolution
  As a system architect
  I want the NodeMetadata schema to support new fields while accepting old data
  So that existing databases remain compatible

  Scenario: Loading legacy data
    Given a raw JSON object with only "cluster_id"
    When I validate it against the NodeMetadata schema
    Then the "dikw_level" field should default to "data"
    And the "is_user_edited" field should default to false
    And the "refinement_history" field should be an empty list
```
