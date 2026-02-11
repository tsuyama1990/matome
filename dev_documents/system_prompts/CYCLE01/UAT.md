# Cycle 01: Core Architecture Refactoring - User Acceptance Test (UAT)

## 1. Test Scenarios

### Scenario 1.1: Default Behavior Preservation
**Objective**: Ensure that refactoring the `SummarizationAgent` to use the Strategy Pattern does not break existing functionality.
*   **Description**: Run the CLI with the default configuration (`--mode default`) and confirm that it produces summaries identical (in structure) to the previous version.
*   **Success Criteria**:
    *   The command `python -m matome.cli run test_data/sample.txt` executes without error.
    *   The generated `summary_all.md` contains valid markdown text.
    *   No "strategy not found" or `AttributeError` exceptions are raised.

### Scenario 1.2: Custom Strategy Injection
**Objective**: Verify that a developer can inject a custom `PromptStrategy` into the `SummarizationAgent`.
*   **Description**: Create a small Python script that defines a `ToyStrategy` (e.g., one that just uppercases the text) and passes it to the agent.
*   **Success Criteria**:
    *   The script runs successfully.
    *   The output summary is clearly the result of the custom strategy (e.g., all uppercase).
    *   This proves the architecture is decoupled.

### Scenario 1.3: Metadata Schema Validation
**Objective**: confirm that `SummaryNode` objects can now store DIKW-related metadata without validation errors.
*   **Description**: Create a `SummaryNode` with `dikw_level="wisdom"` and `refinement_history` populated. Save and load it from `DiskChunkStore`.
*   **Success Criteria**:
    *   The node is saved to `chunks.db` without error.
    *   When loaded back, `node.metadata.dikw_level` is correctly set to `DIKWLevel.WISDOM`.
    *   The `refinement_history` list is preserved.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Prompt Strategy Integration

  Scenario: Default Summarization
    GIVEN the SummarizationAgent is initialized without arguments
    WHEN I call the summarize method with "This is a test."
    THEN the agent should use the BaseSummaryStrategy
    AND the result should be a standard summary string

  Scenario: Custom Strategy Execution
    GIVEN I have defined a UppercaseStrategy class
    AND I initialize the SummarizationAgent with this strategy
    WHEN I call the summarize method with "hello world"
    THEN the agent should use the UppercaseStrategy.generate_prompt
    AND the result should be "HELLO WORLD" (processed by the strategy)

Feature: Enhanced Node Metadata

  Scenario: Storing DIKW Attributes
    GIVEN a SummaryNode object
    WHEN I set metadata.dikw_level to "knowledge"
    AND I add a record to metadata.refinement_history
    THEN the node should be valid according to the Pydantic schema
    AND I should be able to serialize the node to JSON
    AND I should be able to deserialize it back without data loss
```
