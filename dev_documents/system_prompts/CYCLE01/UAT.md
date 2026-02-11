# Cycle 01: Core Refactoring & Metadata Standardization - User Acceptance Testing (UAT)

## 1. Test Scenarios

These scenarios verify that the architectural changes (Strategy Pattern, Metadata) function correctly without breaking the existing system.

### Scenario 1.1: Metadata Validation (The "Schema Check")
**Priority:** High
**Goal:** Ensure that all new and existing nodes conform to the new metadata schema.

**Steps:**
1.  **Setup:** Open a Jupyter Notebook (`cycle01_metadata_check.ipynb`).
2.  **Action:** Import `SummaryNode` and `NodeMetadata` (or `DIKWLevel`).
3.  **Action:** Create a `SummaryNode` with valid metadata `{'dikw_level': 'wisdom'}`.
4.  **Action:** Create a `SummaryNode` with **invalid** metadata `{'dikw_level': 'super_wisdom'}`.
5.  **Verify:** The valid node is created successfully. The invalid node raises a `ValidationError` (or equivalent Pydantic error).

### Scenario 1.2: Strategy Injection (The "Brain Swap")
**Priority:** High
**Goal:** Confirm that `SummarizationAgent` effectively delegates prompt generation to the injected strategy.

**Steps:**
1.  **Setup:** In the notebook, define a `MockStrategy` class that implements `PromptStrategy`.
    ```python
    class MockStrategy:
        def create_prompt(self, text, context=None):
            return f"Summarize this like a pirate: {text}"
    ```
2.  **Action:** Instantiate `SummarizationAgent` passing this `MockStrategy`.
3.  **Action:** Call `agent.summarize("Hello World")` (mocking the LLM response if needed).
4.  **Verify:** Inspect the internal log or use a spy to confirm that the prompt sent to the LLM started with "Summarize this like a pirate".

### Scenario 1.3: Regression Safety (The "Do No Harm")
**Priority:** Critical
**Goal:** Ensure the standard CLI command still works exactly as before.

**Steps:**
1.  **Setup:** Have a sample text file `test_data/sample.txt`.
2.  **Action:** Run `python -m matome.cli run test_data/sample.txt`.
3.  **Verify:** The process completes without error.
4.  **Verify:** A `summary.md` (or equivalent output) is generated.
5.  **Verify:** The content of the summary is coherent, proving the default `BaseSummaryStrategy` is working correctly.

## 2. Behavior Definitions (Gherkin)

### Feature: Flexible Prompting

```gherkin
Feature: Summarization Strategy
  As a developer
  I want to inject different prompt strategies into the agent
  So that I can change the summarization behavior without modifying the agent code

  Scenario: Default strategy is used when none is provided
    Given I instantiate a SummarizationAgent without arguments
    When I call summarize with text "Alpha"
    Then the agent should use the BaseSummaryStrategy
    And the prompt should follow the standard template

  Scenario: Custom strategy is used when injected
    Given I have a strategy "PirateStrategy"
    When I instantiate a SummarizationAgent with "PirateStrategy"
    And I call summarize with text "Bravo"
    Then the agent should use the "PirateStrategy"
    And the prompt should contain pirate terminology
```

### Feature: Metadata Integrity

```gherkin
Feature: Node Metadata
  As a system
  I want to ensure all nodes have a valid DIKW level
  So that the semantic zooming engine can filter them correctly

  Scenario: Valid DIKW Level
    Given a metadata dict with dikw_level "wisdom"
    When I create a SummaryNode
    Then the node is valid

  Scenario: Invalid DIKW Level
    Given a metadata dict with dikw_level "unknown_level"
    When I create a SummaryNode
    Then a ValidationError should be raised
```
