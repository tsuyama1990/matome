# Cycle 01 Specification: Core Refactoring & Foundation

## 1. Summary

The primary objective of **Cycle 01** is to establish the architectural foundation required for the "Knowledge Installation" features without breaking the existing summarization capabilities. This involves a critical refactoring of the `SummarizationAgent` to adopt the **Strategy Pattern**, decoupling the *execution* of an LLM call from the *construction* of the prompt. Additionally, we will update the `NodeMetadata` schema to support the future DIKW hierarchy and interactive refinement features. By the end of this cycle, the system will behave exactly as before from a user's perspective, but the internal code structure will be ready for the specialized logic of Cycle 02.

## 2. System Architecture

The following file structure illustrates the changes for this cycle. New files are marked in **bold**.

```ascii
src/
├── domain_models/
│   ├── __init__.py
│   └── **data_schema.py**      # Modified: Update NodeMetadata
├── matome/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── **strategies.py**   # New: Concrete strategy implementations
│   │   └── **summarizer.py**   # Modified: Inject PromptStrategy
│   ├── **interfaces.py**       # New: Define PromptStrategy Protocol
│   ├── engines/
│   │   └── raptor.py           # Touch: Ensure compatibility
│   └── utils.py
└── ...
```

### Key Changes
1.  **`src/matome/interfaces.py`**: Defines the `PromptStrategy` Protocol.
2.  **`src/matome/agents/strategies.py`**: Implements `BaseSummaryStrategy` (the existing "Chain of Density" logic).
3.  **`src/matome/agents/summarizer.py`**: Refactored to accept a `strategy` argument in its `summarize` method (or init).
4.  **`src/domain_models/data_schema.py`**: Adds `dikw_level`, `is_user_edited`, and `refinement_history` fields to `NodeMetadata`.

## 3. Design Architecture

### 3.1. Prompt Strategy Pattern

The core design change is the introduction of the `PromptStrategy` Protocol. This allows us to swap out the prompt engineering logic at runtime.

```python
# src/matome/interfaces.py
from typing import Protocol, Any

class PromptStrategy(Protocol):
    """Protocol for defining how to construct prompts and parse LLM outputs."""

    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """Constructs the prompt string for the LLM."""
        ...

    def parse_output(self, response: str) -> dict[str, Any]:
        """Parses the raw string response into a structured dictionary."""
        ...
```

The existing summarization logic (Chain of Density) will be encapsulated in `BaseSummaryStrategy`.

### 3.2. Node Metadata Schema

The `NodeMetadata` model in `src/domain_models/data_schema.py` is the single source of truth for a node's semantic properties.

```python
# src/domain_models/data_schema.py
from enum import StrEnum
from pydantic import BaseModel, Field

class DIKWLevel(StrEnum):
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"

class NodeMetadata(BaseModel):
    # Existing fields...
    cluster_id: int | None = None

    # New fields
    dikw_level: DIKWLevel = Field(default=DIKWLevel.DATA, description="The abstraction level of this node.")
    is_user_edited: bool = Field(default=False, description="True if the content has been manually refined by a user.")
    refinement_history: list[str] = Field(default_factory=list, description="History of refinement instructions applied to this node.")
```

**Constraints & Validation:**
*   `dikw_level` must be a valid enum member.
*   `refinement_history` is an append-only list.
*   Existing databases must load correctly; Pydantic's `default` values ensure backward compatibility.

## 4. Implementation Approach

### Step 1: Define Interfaces
Create `src/matome/interfaces.py` and define the `PromptStrategy` protocol. This ensures a strict contract for all future strategies.

### Step 2: Implement Base Strategy
Create `src/matome/agents/strategies.py`. Move the existing prompt template and parsing logic from `SummarizationAgent` into a new class `BaseSummaryStrategy`. This class should implement `PromptStrategy`.

### Step 3: Update SummarizationAgent
Modify `SummarizationAgent` in `src/matome/agents/summarizer.py`.
*   Remove the hardcoded prompt templates.
*   Update `summarize()` method to accept an optional `strategy: PromptStrategy`.
*   If `strategy` is not provided, default to `BaseSummaryStrategy()`.
*   Update the `invoke` call to use `strategy.format_prompt(text)` and `strategy.parse_output(response)`.

### Step 4: Update Data Schema
Modify `src/domain_models/data_schema.py`.
*   Import `StrEnum` (or `Enum` if < 3.11, but project is 3.11+).
*   Add the `DIKWLevel` enum.
*   Add the new fields to `NodeMetadata`.

### Step 5: Verify & Refactor Callers
Search for usages of `SummarizationAgent` (e.g., in `RaptorEngine`) and ensure they still work. Since we default the strategy in the arguments, no changes *should* be needed in callers, but verification is required.

## 5. Test Strategy

### 5.1. Unit Testing
*   **`tests/test_strategies.py`**:
    *   Test `BaseSummaryStrategy.format_prompt()`: Verify it produces the expected string format.
    *   Test `BaseSummaryStrategy.parse_output()`: Verify it correctly extracts the summary from a mock LLM response (handling JSON or plain text as per current logic).
*   **`tests/test_summarizer.py`**:
    *   Test `SummarizationAgent.summarize()` with a **MockStrategy**. Create a simple mock strategy that returns "MOCK PROMPT" and parses to `{"summary": "MOCK RESULT"}`. Verify the agent uses it correctly.
    *   This confirms the decoupling works.

### 5.2. Integration Testing
*   **`tests/test_schema_migration.py`**:
    *   Create a `NodeMetadata` object using the *old* schema (simulate by passing only old fields dict).
    *   Verify it instantiates correctly with `dikw_level=DIKWLevel.DATA` and `is_user_edited=False`.
*   **Existing Tests**:
    *   Run the full existing test suite (`pytest`). All tests must pass. If `SummarizationAgent` refactoring broke the default behavior, these tests will catch it.
