# Cycle 01: Core Architecture Refactoring - Specification

## 1. Summary

The primary objective of Cycle 01 is to refactor the existing `matome` codebase to support the sophisticated "Semantic Zooming" capabilities required for Matome 2.0. Currently, the `SummarizationAgent` has summarization logic tightly coupled within its `summarize` method. This makes it difficult to implement different styles of summarization (Wisdom vs. Knowledge vs. Action) without creating a messy web of `if/else` statements.

In this cycle, we will implement the **Strategy Pattern** for prompt generation. We will extract the prompt construction and output parsing logic into a new `PromptStrategy` protocol. The `SummarizationAgent` will be updated to accept a strategy instance, allowing its behavior to be modified at runtime. To ensure backward compatibility and a smooth transition, we will implement a `BaseSummaryStrategy` that replicates the current "Chain of Density" logic.

Additionally, we will update the `SummaryNode` data model to include the necessary fields for the DIKW (Data, Information, Knowledge, Wisdom) hierarchy. This involves adding `dikw_level`, `refinement_history`, and `is_user_edited` to the `NodeMetadata` schema.

This refactoring is a foundational step. It does not change the user-facing behavior of the CLI yet, but it prepares the internal machinery for the specific DIKW strategies to be implemented in Cycle 02.

## 2. System Architecture

The following file structure highlights the files that will be created or modified in this cycle.

```text
src/
├── domain_models/
│   ├── **metadata.py**       # UPDATED: Add DIKW fields to NodeMetadata
│   └── chunk.py              # (No change, uses metadata)
├── matome/
│   ├── agents/
│   │   ├── **strategies.py** # CREATED: Define PromptStrategy protocol & BaseSummaryStrategy
│   │   └── **summarizer.py** # UPDATED: Inject strategy into SummarizationAgent
│   └── interfaces.py         # CREATED: (Optional) If we need a shared interface definition
tests/
├── **test_strategies.py**    # CREATED: Unit tests for BaseSummaryStrategy
└── test_summarizer.py        # UPDATED: Ensure agent works with new strategy
```

### Key Components

*   **`src/matome/agents/strategies.py`**: This new module will house the `PromptStrategy` protocol and the `BaseSummaryStrategy` concrete class.
*   **`src/matome/agents/summarizer.py`**: The `SummarizationAgent` class will be modified to accept an optional `strategy: PromptStrategy` in its `summarize` method. If no strategy is provided, it will default to `BaseSummaryStrategy`.
*   **`src/domain_models/metadata.py`**: The `NodeMetadata` Pydantic model will be expanded.

## 3. Design Architecture

This section details the Pydantic models and Protocol definitions.

### 3.1. NodeMetadata (Updated)

We will update `NodeMetadata` in `src/domain_models/metadata.py`.

```python
from enum import StrEnum
from pydantic import BaseModel, Field
from typing import List, Optional

class DIKWLevel(StrEnum):
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"

class RefinementRecord(BaseModel):
    instruction: str
    original_text: str
    refined_text: str
    timestamp: float

class NodeMetadata(BaseModel):
    # Existing fields
    source_chunk_ids: List[str] = Field(default_factory=list)
    # New fields for Matome 2.0
    dikw_level: Optional[DIKWLevel] = None
    is_user_edited: bool = False
    refinement_history: List[RefinementRecord] = Field(default_factory=list)

    model_config = {
        "extra": "allow" # Allow for forward compatibility
    }
```

**Constraints**:
*   `refinement_history` should be append-only.
*   `dikw_level` is optional for now to support legacy nodes, but should be populated for new nodes.

### 3.2. PromptStrategy (Protocol)

We will define a `PromptStrategy` protocol in `src/matome/interfaces.py` (or `strategies.py` if preferred to keep it together).

```python
from typing import Protocol, List

class PromptStrategy(Protocol):
    """Defines how to prompt the LLM and parse its output."""

    def generate_prompt(self, text: str | List[str], context: str = "") -> str:
        """
        Constructs the prompt for the LLM.

        Args:
            text: The content to summarize (single string or list of chunks).
            context: Optional context (e.g., parent node summary).
        """
        ...

    def parse_output(self, response: str) -> str:
        """
        Parses the raw LLM response into the final summary text.
        Handles cleaning, stripping, or JSON parsing if needed.
        """
        ...
```

### 3.3. BaseSummaryStrategy (Concrete Implementation)

This class will encapsulate the current logic found in `SummarizationAgent`.

```python
class BaseSummaryStrategy:
    """Implements the standard Chain of Density summarization."""

    def generate_prompt(self, text: str | List[str], context: str = "") -> str:
        # Implementation of the existing prompt template
        combined_text = "\n".join(text) if isinstance(text, list) else text
        return f"Summarize the following text concisely:\n\n{combined_text}"

    def parse_output(self, response: str) -> str:
        return response.strip()
```

## 4. Implementation Approach

### Step 1: Define the Interfaces
1.  Create `src/matome/agents/strategies.py`.
2.  Define the `PromptStrategy` protocol.
3.  Define the `DIKWLevel` enum and `RefinementRecord` model in `src/domain_models/metadata.py`.

### Step 2: Implement Base Strategy
1.  Extract the prompt template currently hardcoded in `SummarizationAgent` into `BaseSummaryStrategy` in `src/matome/agents/strategies.py`.
2.  Ensure `BaseSummaryStrategy` handles list-of-strings vs. single-string input correctly.

### Step 3: Refactor SummarizationAgent
1.  Modify `SummarizationAgent.__init__` (or the `summarize` method) to accept a `strategy` argument.
2.  In `SummarizationAgent.summarize`, replace the hardcoded prompt generation with `strategy.generate_prompt()`.
3.  Replace the output handling with `strategy.parse_output()`.
4.  Ensure that if `strategy` is `None`, it defaults to `BaseSummaryStrategy()`.

### Step 4: Verify Backward Compatibility
1.  Run existing tests to ensure `SummarizationAgent` still behaves as expected with the default strategy.

## 5. Test Strategy

### 5.1. Unit Testing

**`tests/test_strategies.py`**
*   **Test `BaseSummaryStrategy`**:
    *   Input: A list of strings.
    *   Expected Output: A formatted prompt string containing the joined text.
    *   Input: A raw LLM response with whitespace.
    *   Expected Output: A stripped string.

**`tests/test_metadata.py`**
*   **Test `NodeMetadata`**:
    *   Verify `dikw_level` accepts valid enum values ("wisdom", "knowledge").
    *   Verify `dikw_level` rejects invalid strings (if Pydantic validation is strict).
    *   Verify `refinement_history` can store a valid `RefinementRecord`.

### 5.2. Integration Testing

**`tests/test_summarizer_integration.py`**
*   **Test Agent with Default Strategy**:
    *   Initialize `SummarizationAgent` without arguments.
    *   Call `summarize("test text")`.
    *   Assert output is a valid string.
*   **Test Agent with Mock Strategy**:
    *   Define a `MockStrategy` that returns "MOCKED PROMPT" and parses to "MOCKED RESULT".
    *   Initialize `SummarizationAgent`.
    *   Call `summarize("test", strategy=MockStrategy())`.
    *   Assert the prompt sent to the LLM (if mockable) or the result matches the mock strategy's behavior.
