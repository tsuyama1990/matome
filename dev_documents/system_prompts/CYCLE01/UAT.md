# Cycle 01: User Acceptance Testing (UAT)

## 1. Test Scenarios

### Scenario A: Verify Default Behavior
*   **ID**: S01-01
*   **Priority**: High
*   **Description**: Ensure that the refactored `SummarizationAgent` still works correctly with the default strategy, producing summaries as expected.
*   **Preconditions**:
    *   System is built with the new `PromptStrategy` architecture.
    *   `test_data/sample.txt` exists.
*   **Steps**:
    1.  Run the CLI command: `uv run matome run test_data/sample.txt`.
    2.  Check the output directory for `summary_all.md`.
    3.  Verify the summary content is coherent (not empty or error messages).

### Scenario B: Verify Strategy Injection (Developer Experience)
*   **ID**: S01-02
*   **Priority**: Medium
*   **Description**: Verify that a developer can inject a custom `PromptStrategy` into the `SummarizationAgent`.
*   **Preconditions**:
    *   Python environment with `matome` installed in editable mode.
*   **Steps (Code)**:
    ```python
    from matome.agents.summarizer import SummarizationAgent
    from matome.agents.strategies import BaseSummaryStrategy
    from domain_models.config import ProcessingConfig

    # 1. Define a Mock Strategy
    class MockStrategy:
        def format_prompt(self, text: str, context: str = "") -> str:
            return "MOCK_PROMPT"
        def parse_output(self, output: str) -> str:
            return "MOCK_OUTPUT"

    # 2. Initialize Agent with Mock Strategy
    agent = SummarizationAgent(ProcessingConfig(), strategy=MockStrategy())

    # 3. Call Summarize (should use mock logic, though here we'd need to mock LLM too or check internal state)
    # Ideally, we check if agent.strategy is instance of MockStrategy
    assert isinstance(agent.strategy, MockStrategy)
    print("Strategy Injection Successful")
    ```

## 2. Behavior Definitions (Gherkin)

### Feature: Pluggable Summarization Strategies

**Scenario: Default summarization uses BaseSummaryStrategy**
  **GIVEN** a `SummarizationAgent` initialized without a strategy
  **WHEN** I call `summarize("some text")`
  **THEN** it should use `BaseSummaryStrategy` internally
  **AND** produce a standard summary string

**Scenario: Custom strategy overrides default behavior**
  **GIVEN** a custom `WisdomStrategy` that always prepends "WISDOM:"
  **AND** a `SummarizationAgent` initialized with this strategy
  **WHEN** I call `summarize("some text")`
  **THEN** the prompt sent to the LLM should be formatted by `WisdomStrategy`
