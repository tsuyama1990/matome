# Cycle 01 User Acceptance Test (UAT): Core Architecture

## 1. Test Scenarios

Since Cycle 01 is an architectural refactoring phase with no user-facing UI changes, the "User" in this context is the **Developer** or the **Future System**. The acceptance criteria focus on API stability, data integrity, and the successful decoupling of components.

### Scenario ID: C01-01 (Data Model Robustness)
**Priority**: High
**Objective**: Verify that the new `NodeMetadata` schema correctly handles data integrity and backward compatibility.
**Description**:
As a developer, I need to ensure that when I save and load nodes, the DIKW metadata is preserved. I also need to ensure that existing databases (which lack this metadata) can still be loaded without crashing the system.
**Steps**:
1.  Create a Jupyter Notebook `tests/uat/C01_metadata_check.ipynb`.
2.  Import `SummaryNode` and `NodeMetadata`.
3.  **Positive Test**: Instantiate a node with `dikw_level='wisdom'`. Serialize it to JSON. Deserialize it. Verify the level remains 'wisdom'.
4.  **Negative Test**: Try to instantiate a node with `dikw_level='magic'`. Verify that a Validation Error occurs.
5.  **Migration Test**: Create a dictionary mimicking an old node: `{'text': '...', 'metadata': {'source': 'file.txt'}}`. Pass this to `SummaryNode`. Verify that `node.metadata.dikw_level` defaults to 'data' and the `source` field is preserved.

### Scenario ID: C01-02 (Strategy Injection)
**Priority**: High
**Objective**: Verify that the `SummarizationAgent` functionality remains unchanged while using the new Strategy pattern.
**Description**:
As a system architect, I need to confirm that extracting the prompt logic into `BaseSummaryStrategy` hasn't altered the output or behavior of the agent.
**Steps**:
1.  Create a Jupyter Notebook `tests/uat/C01_strategy_check.ipynb`.
2.  Initialize `SummarizationAgent` *without* arguments (should default to BaseStrategy).
3.  Run `agent.summarize(chunks=["Hello world"])` (Mocking the LLM is acceptable here, or use a cheap model).
4.  Initialize `SummarizationAgent` *with* a custom `TestStrategy` that always returns "FIXED PROMPT".
5.  Run `agent.summarize`. Verify that the underlying prompt constructed (if accessible via logs or debug) matches the strategy's logic.

## 2. Behavior Definitions (Gherkin)

### Feature: Node Metadata Management

**Scenario**: Saving a new Wisdom node
  **GIVEN** I have a text summary "Philosophy of Life"
  **WHEN** I create a SummaryNode with `dikw_level="wisdom"`
  **THEN** the node should be valid
  **AND** `node.metadata.dikw_level` should be equal to `DIKWLevel.WISDOM`

**Scenario**: Loading legacy data
  **GIVEN** a raw database record with metadata `{"timestamp": "12345"}`
  **WHEN** I load this record into a SummaryNode object
  **THEN** the system should not raise an error
  **AND** `node.metadata.dikw_level` should automatically be set to `DIKWLevel.DATA`
  **AND** `node.metadata.timestamp` should be accessible

### Feature: Prompt Strategy Execution

**Scenario**: Default Strategy Usage
  **GIVEN** a `SummarizationAgent` initialized with no arguments
  **WHEN** I call the `summarize` method
  **THEN** it should use the `BaseSummaryStrategy`
  **AND** the generated prompt should match the legacy prompt format

**Scenario**: Custom Strategy Injection
  **GIVEN** a class `PirateStrategy` that starts prompts with "Ahoy matey"
  **WHEN** I initialize `SummarizationAgent` with `prompt_strategy=PirateStrategy()`
  **AND** I call the `summarize` method
  **THEN** the LLM should receive a prompt starting with "Ahoy matey"
