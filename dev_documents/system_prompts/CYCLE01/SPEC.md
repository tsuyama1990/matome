# Cycle 01: Core Refactoring (Prompt Strategy Pattern)

## 1. Summary

The goal of this cycle is to decouple the summarization logic (prompts and parsing) from the `SummarizationAgent`. Currently, the agent likely contains hardcoded prompts or logic for generating summaries. By introducing the **Strategy Pattern**, we prepare the system for Matome 2.0's DIKW requirement, where different tree levels require drastically different prompting strategies (Wisdom vs. Data).

In this cycle, we will define the `PromptStrategy` interface and implement the default behavior (Chain of Density) as `BaseSummaryStrategy`. This ensures no regression in existing functionality while opening the architecture for extension.

## 2. System Architecture

We will modify the `src/matome` package to include new interfaces and strategy implementations.

```ascii
src/matome/
├── agents/
│   ├── **strategies.py**       # [NEW] Contains BaseSummaryStrategy
│   └── **summarizer.py**       # [MOD] Updated to use PromptStrategy
├── **interfaces.py**           # [MOD] Add PromptStrategy Protocol
└── ...
```

### Files to Modify/Create

1.  **`src/matome/interfaces.py`**
    *   **Action**: Add `PromptStrategy` Protocol.
2.  **`src/matome/agents/strategies.py`**
    *   **Action**: Create this file. Implement `BaseSummaryStrategy` (encapsulating current logic).
3.  **`src/matome/agents/summarizer.py`**
    *   **Action**: Refactor `SummarizationAgent` to accept an optional `strategy` argument.

## 3. Design Architecture

### 3.1. PromptStrategy Protocol

We define a strict protocol to ensure all future strategies (Wisdom, Knowledge, etc.) are interchangeable.

```python
class PromptStrategy(Protocol):
    """
    Protocol for defining how to prompt the LLM and parse its output.
    """
    def format_prompt(self, text: str, context: str = "") -> str:
        """
        Constructs the prompt string to send to the LLM.
        """
        ...

    def parse_output(self, output: str) -> str:
        """
        Parses the raw LLM output into the desired string format.
        (e.g., extracting content from XML tags if used).
        """
        ...
```

### 3.2. BaseSummaryStrategy (Default)

This strategy encapsulates the existing "Chain of Density" or standard summarization logic currently residing in `SummarizationAgent`.

*   **Responsibility**:
    *   `format_prompt`: Returns the standard summarization prompt.
    *   `parse_output`: returns the raw output (or cleaned version).

### 3.3. SummarizationAgent Refactoring

The agent becomes a dumb executor.

*   **Before**:
    ```python
    def summarize(self, text):
        prompt = f"Summarize this: {text}" # Hardcoded
        response = llm.invoke(prompt)
        return response
    ```
*   **After**:
    ```python
    def __init__(self, config, strategy: PromptStrategy = BaseSummaryStrategy()):
        self.strategy = strategy

    def summarize(self, text, strategy: PromptStrategy | None = None):
        # Allow method-level override for dynamic switching
        strat = strategy or self.strategy
        prompt = strat.format_prompt(text)
        response = llm.invoke(prompt)
        return strat.parse_output(response)
    ```

## 4. Implementation Approach

1.  **Define Interface**: Update `src/matome/interfaces.py` with the `PromptStrategy` protocol.
2.  **Extract Logic**: Copy the current prompt logic from `SummarizationAgent` into a new class `BaseSummaryStrategy` in `src/matome/agents/strategies.py`.
3.  **Refactor Agent**: Modify `SummarizationAgent` to use the strategy. Ensure backward compatibility by making the strategy optional (defaulting to `BaseSummaryStrategy`).
4.  **Update Callers**: Check if any other parts of the system instantiate `SummarizationAgent` and update if necessary (though with default args, it should be safe).

## 5. Test Strategy

### 5.1. Unit Testing
*   **Test Strategy Isolation**:
    *   Create `tests/agents/test_strategies.py`.
    *   Verify `BaseSummaryStrategy.format_prompt` returns the expected string.
*   **Test Agent Injection**:
    *   Create a `MockStrategy` in tests.
    *   Initialize `SummarizationAgent` with `MockStrategy`.
    *   Call `summarize` and assert that `MockStrategy.format_prompt` was called.

### 5.2. Integration Testing
*   **Regression Test**: Run the existing `test_summarizer.py` or equivalent integration tests to ensure the refactor hasn't broken the default summarization flow. The external behavior (input text -> summary output) should remain unchanged.
