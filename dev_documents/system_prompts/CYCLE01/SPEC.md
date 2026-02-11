# Cycle 01: Core Logic Refactoring & DIKW Metadata - Specification

## 1. Summary

The primary objective of Cycle 01 is to lay the architectural foundation for the **DIKW (Data, Information, Knowledge, Wisdom)** hierarchy generation without breaking the existing functionality of the system. This involves a significant refactoring of the core summarization logic. Currently, the `SummarizationAgent` contains hardcoded prompts or logic that is tightly coupled to a specific style of summarization. To enable the multi-layered "Semantic Zooming" required for Matome 2.0, we must decouple the *how* (the prompt strategy) from the *who* (the agent executing the LLM call).

We will introduce the **Strategy Pattern** by defining a `PromptStrategy` interface. This will allow us to easily swap between different summarization objectives (e.g., "Generate Wisdom", "Extract Action Items", "Summarize for Context") at runtime. Additionally, we will formalize the data structures required to support the DIKW hierarchy by extending the domain models with a `DIKWLevel` enum and updating the `SummaryNode` metadata schema. This cycle is purely foundational; while no new end-user features will be visible in the CLI output yet, the internal machinery will be ready for the specialized DIKW generation in Cycle 02.

## 2. System Architecture

This cycle focuses on refactoring the `src/matome/agents` and `src/matome/engines` modules and introducing a new `src/matome/strategies` module.

### File Structure

```ascii
src/
├── domain_models/
│   ├── **dikw.py**          # [NEW] DIKW Enums and constants
│   ├── **types.py**         # [MODIFIED] Update NodeMetadata definition
│   └── manifest.py          # [MODIFIED] Ensure SummaryNode accepts new metadata
├── matome/
│   ├── agents/
│   │   └── **summarizer.py** # [MODIFIED] Inject PromptStrategy
│   ├── engines/
│   │   └── raptor.py        # [MODIFIED] Use LegacyStrategy (Backward Compatibility)
│   ├── interfaces.py        # [MODIFIED] Define PromptStrategy Protocol
│   └── strategies/          # [NEW] Strategy Implementations
│       ├── **__init__.py**
│       ├── **base.py**      # [NEW] Base Class / Interface
│       └── **legacy.py**    # [NEW] Existing Logic wrapped as Strategy
```

**Bold** files are those to be created or significantly modified in this cycle.

## 3. Design Architecture

The design centers on strict type safety and separation of concerns using Protocols and Pydantic models.

### 3.1. Domain Models (`src/domain_models/`)

**`dikw.py`**
We introduce an enumeration to strictly type the hierarchy levels.
```python
from enum import Enum

class DIKWLevel(str, Enum):
    WISDOM = "wisdom"       # L1: High abstraction
    KNOWLEDGE = "knowledge" # L2: Structural understanding
    INFORMATION = "information" # L3: Actionable items
    DATA = "data"           # L4: Raw text
```

**`types.py` / `manifest.py`**
We update the metadata definition. While `SummaryNode.metadata` is a `Dict[str, Any]`, we should define a Pydantic model that *can* be used to validate it, or at least document the keys.
```python
from pydantic import BaseModel, Field

class NodeMetadata(BaseModel):
    """Schema for SummaryNode metadata."""
    dikw_level: DIKWLevel | None = None
    is_user_edited: bool = Field(default=False, description="True if manually refined")
    refinement_history: list[str] = Field(default_factory=list)
```
*Constraints:* The `dikw_level` is optional for now to support existing data (which has no level).

### 3.2. Strategy Interface (`src/matome/interfaces.py`)

We define a `Protocol` for the prompt strategy. This ensures any future strategy (Wisdom, Creative, etc.) adheres to the same contract.

```python
from typing import Protocol

class PromptStrategy(Protocol):
    """Interface for summarization prompt strategies."""

    def get_system_prompt(self) -> str:
        """Returns the system instruction (persona)."""
        ...

    def get_user_prompt(self, context: str) -> str:
        """Returns the formatted user prompt with context."""
        ...

    def parse_output(self, output: str) -> str:
        """Post-processes the LLM output (cleaning, formatting)."""
        ...
```

### 3.3. Summarization Agent (`src/matome/agents/summarizer.py`)

The agent is refactored to take a strategy in its `summarize` method (or constructor, but method injection allows one agent to switch strategies).

```python
class SummarizationAgent:
    # ...
    def summarize(self, context: str, strategy: PromptStrategy) -> str:
        system_prompt = strategy.get_system_prompt()
        user_prompt = strategy.get_user_prompt(context)
        # ... call LLM ...
        return strategy.parse_output(response)
```

## 4. Implementation Approach

The implementation will proceed in strictly ordered steps to maintain a working build at all times.

### Step 1: Define Interfaces & Models
1.  Create `src/domain_models/dikw.py` with the `DIKWLevel` enum.
2.  Update `src/matome/interfaces.py` to include `PromptStrategy`.
3.  (Optional) Add `NodeMetadata` model to `src/domain_models/types.py` for reference.

### Step 2: Implement Legacy Strategy
1.  Create `src/matome/strategies/base.py` (abstract base class if needed, or just rely on Protocol).
2.  Create `src/matome/strategies/legacy.py`.
3.  Copy the *existing* prompt logic from `SummarizationAgent` into `LegacyStrategy`.
    -   `get_system_prompt`: Returns the current system prompt.
    -   `get_user_prompt`: Returns the current f-string formatting.
    -   `parse_output`: Returns the output as-is (or with current cleaning logic).

### Step 3: Refactor SummarizationAgent
1.  Modify `SummarizationAgent.summarize` signature to accept `strategy: PromptStrategy`.
2.  Remove the hardcoded prompts from the class.
3.  Update the `__init__` if necessary (e.g., to set a default strategy).

### Step 4: Update RaptorEngine
1.  Open `src/matome/engines/raptor.py`.
2.  Locate where `agent.summarize` is called.
3.  Instantiate `LegacyStrategy` (or inject it) and pass it to the agent.
    -   `summary = self.agent.summarize(context, strategy=LegacyStrategy())`

### Step 5: Verification
1.  Run existing tests. They should pass (or fail if they mocked the old method signature).
2.  Update tests to pass a mock strategy.

## 5. Test Strategy

### Unit Testing
*   **`tests/unit/test_strategies.py`**:
    *   Test `LegacyStrategy`: Ensure it returns the exact strings expected (copy-paste comparison with old prompts).
*   **`tests/unit/test_summarization_agent.py`**:
    *   Mock `PromptStrategy`.
    *   Call `agent.summarize(context="test", strategy=mock_strategy)`.
    *   Assert that `mock_strategy.get_system_prompt` and `get_user_prompt` were called.
    *   Assert the output matches `mock_strategy.parse_output`.

### Integration Testing
*   **`tests/integration/test_refactoring_regression.py`**:
    *   Run the full `RaptorEngine` pipeline on a small text file.
    *   Assert that it completes without error.
    *   Assert that the output is qualitatively similar to the previous version (since we are using `LegacyStrategy`, it should be identical).
*   **`tests/unit/test_domain_models.py`**:
    *   Verify `DIKWLevel` enum values.
    *   Verify `SummaryNode` can accept `metadata={"dikw_level": "wisdom"}` without validation error (if using Pydantic `extra='allow'` or updated model).
