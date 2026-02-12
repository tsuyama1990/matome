# Cycle 01 Specification: Core Refactoring (Strategy Pattern)

## 1. Summary

The primary objective of Cycle 01 is to refactor the existing `SummarizationAgent` to support multiple summarization modes. Currently, the agent's logic for prompting and parsing is tightly coupled with its execution logic. This monolithic design prevents us from easily implementing the DIKW (Data, Information, Knowledge, Wisdom) hierarchy required for Matome 2.0. By introducing a **Strategy Pattern**, we will decouple the "how" of summarization (the strategy) from the "execution" (the agent).

This cycle focuses purely on architectural refactoring and regression testing. The external behavior of the CLI should remain identical to Cycle 0, but the internal structure will become flexible and extensible. This foundational work is critical for subsequent cycles, where we will introduce specific strategies for Wisdom, Knowledge, and Information generation without modifying the core agent logic.

## 2. System Architecture

This section details the architectural changes required to implement the Strategy Pattern.

### 2.1. File Structure

We will introduce a new module for strategies and modify the existing agent and CLI.

```ascii
src/
├── matome/
│   ├── agents/
│   │   ├── strategies.py    # [NEW] Protocol & Base Implementation
│   │   └── summarizer.py    # [MODIFIED] Strategy Injection
│   └── cli.py               # [MODIFIED] Inject Default Strategy
```

**New Files:**
- **`src/matome/agents/strategies.py`**: This file will house the `PromptStrategy` Protocol and the concrete `BaseSummaryStrategy` class.

**Modified Files:**
- **`src/matome/agents/summarizer.py`**: The `SummarizationAgent` class will be updated to accept a `strategy` instance in its constructor. The hardcoded prompt templates and parsing logic will be removed and delegated to the strategy.
- **`src/matome/cli.py`**: The CLI entry point will be updated to instantiate the `BaseSummaryStrategy` and pass it to the agent, ensuring backward compatibility.

### 2.2. Component Interaction

The interaction flow shifts from a direct call to a delegated execution model.

**Before (Cycle 0):**
`CLI` -> `SummarizationAgent` (Hardcoded Prompt) -> `LLM` -> `SummarizationAgent` (Hardcoded Parsing) -> `SummaryNode`

**After (Cycle 01):**
`CLI` -> `BaseSummaryStrategy` (Instance) -> `SummarizationAgent` (Injected Strategy)
`SummarizationAgent` -> `strategy.format_prompt(text)` -> `Prompt String`
`SummarizationAgent` -> `LLM(Prompt String)` -> `Raw Response`
`SummarizationAgent` -> `strategy.parse_output(Raw Response)` -> `Structured Data` -> `SummaryNode`

### 2.3. Class Blueprint

**`src/matome/agents/strategies.py`**

```python
from typing import Protocol, Any, Dict

class PromptStrategy(Protocol):
    """
    Interface for summarization strategies.
    Implementations must define how to construct prompts and parse responses.
    """
    def format_prompt(self, text: str, context: Dict[str, Any] | None = None) -> str:
        """
        Constructs the prompt string from the input text and optional context.
        """
        ...

    def parse_output(self, response: str) -> Dict[str, Any]:
        """
        Parses the raw LLM response string into a structured dictionary.
        Must return at least {'summary': str}.
        """
        ...

class BaseSummaryStrategy:
    """
    Implements the default summarization logic (Chain of Density).
    Preserves the behavior of Cycle 0.
    """
    def format_prompt(self, text: str, context: Dict[str, Any] | None = None) -> str:
        # Implementation of the existing Chain of Density template
        ...

    def parse_output(self, response: str) -> Dict[str, Any]:
        # Implementation of the existing parsing logic (handling raw strings)
        return {"summary": response.strip()}
```

**`src/matome/agents/summarizer.py`**

```python
class SummarizationAgent:
    def __init__(self, llm: BaseChatModel, strategy: PromptStrategy):
        self.llm = llm
        self.strategy = strategy

    def summarize(self, text: str | List[str], context: Dict[str, Any] | None = None) -> SummaryNode:
        # ... (handling list input logic)
        prompt = self.strategy.format_prompt(text, context)
        response = self.llm.invoke(prompt)
        parsed_data = self.strategy.parse_output(response.content)
        return SummaryNode(**parsed_data)
```

## 3. Design Architecture

### 3.1. Domain Concepts

**PromptStrategy (Protocol)**
The `PromptStrategy` is the core abstraction for this cycle. It represents a "recipe" for transforming raw text into a summary. By defining it as a Protocol, we ensure that any future strategy (e.g., specific to legal documents, medical texts, or DIKW levels) can be plugged into the system without changing the agent's code.
- **Invariants:**
    - `format_prompt` must return a string.
    - `parse_output` must return a dictionary with at least a `summary` key.
    - Implementations should be stateless regarding the text processing (i.e., they shouldn't store the text internally between calls).

**BaseSummaryStrategy (Concrete Strategy)**
This class encapsulates the legacy logic.
- **Role:** To ensure backward compatibility and serve as the default behavior.
- **Logic:** It uses the "Chain of Density" technique (implicitly or explicitly depending on the Cycle 0 implementation) to produce dense summaries.
- **Output:** It assumes the LLM returns a raw string and wraps it in a simple dictionary `{'summary': ...}`. This avoids breaking the existing pipeline which expects a `SummaryNode` with a `summary` field.

### 3.2. Data Flow & validation
- **Input:** The `SummarizationAgent.summarize` method accepts `text` (str or List[str]) and optional `context` (dict).
- **Processing:** The strategy takes this input. If `text` is a list, the strategy might join it or process it specifically (though `BaseSummaryStrategy` likely joins it).
- **Validation:** The `parse_output` method is responsible for validating the LLM's response structure. For `BaseSummaryStrategy`, validation is minimal (just string stripping). Future strategies (Cycle 02) will enforce stricter schema validation (e.g., JSON parsing).
- **Output:** The agent constructs a `SummaryNode` using the dictionary returned by the strategy. Pydantic validation on `SummaryNode` ensures the final object is valid.

## 4. Implementation Approach

This cycle will be implemented in four distinct steps to ensure stability.

### Step 1: Define the Protocol
Create `src/matome/agents/strategies.py`. Define the `PromptStrategy` protocol using `typing.Protocol`. This establishes the contract for all future work.

### Step 2: Extract Logic to Base Strategy
Copy the existing prompt template and parsing logic from `src/matome/agents/summarizer.py` into the `BaseSummaryStrategy` class in `strategies.py`.
- **Caution:** Ensure that any specific handling of input types (lists vs strings) is correctly migrated or handled by the agent before calling the strategy.
- **Output:** The `parse_output` method should return `{"summary": cleaned_response}`.

### Step 3: Refactor SummarizationAgent
Modify `src/matome/agents/summarizer.py`.
- Update `__init__` to accept `strategy: PromptStrategy`.
- Remove the hardcoded prompt and parsing methods.
- In `summarize`, call `self.strategy.format_prompt` and `self.strategy.parse_output`.
- **Self-Correction/Refinement:** Ensure that the `llm` instance variable is still correctly managed.

### Step 4: Update Consumers (CLI)
Modify `src/matome/cli.py`.
- Import `BaseSummaryStrategy`.
- In the command that initializes `SummarizationAgent`, instantiate `strategy = BaseSummaryStrategy()`.
- Pass this strategy to the agent's constructor.

### Step 5: Verification
Run the existing tests. If they fail (because they instantiate `SummarizationAgent` without a strategy), update the test setup to pass a mock or real `BaseSummaryStrategy`.

## 5. Test Strategy

Testing in this cycle is primarily about preventing regression.

### 5.1. Unit Testing
**File:** `tests/agents/test_strategies.py` (New)
- **Test Case 1: Base Strategy Prompting**
    - **Input:** "Hello World"
    - **Action:** Call `BaseSummaryStrategy().format_prompt("Hello World")`
    - **Assertion:** The returned string contains "Hello World" and matches the expected template structure.
- **Test Case 2: Base Strategy Parsing**
    - **Input:** "  This is a summary.  "
    - **Action:** Call `BaseSummaryStrategy().parse_output(...)`
    - **Assertion:** Returns `{"summary": "This is a summary."}`.

### 5.2. Integration Testing
**File:** `tests/agents/test_summarizer_refactor.py` (New/Modified)
- **Test Case 1: Agent with Strategy**
    - **Setup:** Create `SummarizationAgent` with `BaseSummaryStrategy` and a mock LLM.
    - **Action:** Call `agent.summarize("Content")`.
    - **Assertion:** The mock LLM is called with the correct prompt. The agent returns a `SummaryNode` containing the mock response.
- **Test Case 2: Missing Strategy**
    - **Setup:** Attempt to instantiate `SummarizationAgent` without a strategy.
    - **Assertion:** Raises `TypeError` (caught by static analysis/mypy, or runtime if checked).

### 5.3. Regression Testing
**Manual/CLI Check:**
- Run the CLI command against a sample file (`uv run matome run data/sample.txt`).
- Verify that the output `chunks.db` contains summaries.
- Verify that no crash occurs.
