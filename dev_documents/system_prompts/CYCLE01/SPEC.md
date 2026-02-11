# Cycle 01: Core Refactoring & Metadata Standardization - Specification

## 1. Summary

This cycle lays the groundwork for the entire Matome 2.0 system. The primary goal is to refactor the existing monolithic `SummarizationAgent` to use a flexible `PromptStrategy` pattern. This decoupling is essential for the future "Semantic Zooming" and "Interactive Refinement" features, which require different prompting logic based on the DIKW level and user intent. Additionally, we will standardize the `metadata` field of the `SummaryNode` to strictly type the DIKW levels and track refinement history, ensuring data integrity across the system. This cycle focuses purely on architectural restructuring without changing the external behavior of the CLI (Regression Safety).

## 2. System Architecture

The following file structure highlights the new and modified components for this cycle. The key addition is the `strategies.py` module within the `agents` package.

```ascii
src/
├── domain_models/
│   ├── manifest.py            # MODIFY: Update SummaryNode metadata schema
│   └── types.py               # MODIFY: Add DIKWLevel enum
├── matome/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── summarization.py   # MODIFY: Inject PromptStrategy
│   │   └── **strategies.py**  # NEW: Define Protocol and Concrete Strategies
│   └── engines/
│       └── raptor.py          # MODIFY: Pass default strategy
```

**Key Changes:**
1.  **`src/matome/agents/strategies.py`**: A new file defining the `PromptStrategy` protocol and the `BaseSummaryStrategy` (which encapsulates the current logic).
2.  **`src/matome/agents/summarization.py`**: Modified to accept a `strategy` argument in its `summarize` method (or constructor), removing hardcoded prompt strings.
3.  **`src/domain_models/manifest.py`**: Enhanced `SummaryNode` (or a new `NodeMetadata` model) to include `dikw_level` and `refinement_history`.

## 3. Design Architecture

### 3.1. Prompt Strategy Pattern

To enable dynamic switching of summarization logic, we introduce the Strategy Pattern.

**Protocol Definition:**
```python
from typing import Protocol, Any

class PromptStrategy(Protocol):
    """
    Interface for generating prompts for the LLM.
    """
    def create_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """
        Generates the prompt string to be sent to the LLM.

        Args:
            text: The input text chunk(s) to summarize.
            context: Optional context (e.g., existing summary, tree level).

        Returns:
            The formatted prompt string.
        """
        ...
```

**Concrete Implementation (Base Strategy):**
The `BaseSummaryStrategy` will contain the logic currently hardcoded in `SummarizationAgent`. This ensures that the default behavior remains unchanged.

### 3.2. Node Metadata Standardization

We must enforce structure on the flexible `metadata` dictionary to support the DIKW hierarchy.

**New Enums and Models:**
```python
from enum import StrEnum
from pydantic import BaseModel, Field

class DIKWLevel(StrEnum):
    WISDOM = "wisdom"       # L1
    KNOWLEDGE = "knowledge" # L2
    INFORMATION = "information" # L3
    DATA = "data"           # L4 (Leaf chunks)

class NodeMetadata(BaseModel):
    """
    Standardized metadata for SummaryNodes.
    """
    dikw_level: DIKWLevel = Field(
        default=DIKWLevel.DATA,
        description="The abstraction level of this node."
    )
    is_user_edited: bool = Field(
        default=False,
        description="True if the node content was refined by a user."
    )
    refinement_history: list[str] = Field(
        default_factory=list,
        description="Audit trail of refinement instructions."
    )
    # Allow extra fields for backward compatibility
    model_config = {"extra": "allow"}
```

**Integration:**
The `SummaryNode` in `src/domain_models/manifest.py` should be updated to use this `NodeMetadata` model, or validation logic should be added to ensure these fields exist when necessary.

## 4. Implementation Approach

### Step 1: Define Enums and Metadata
1.  Create `DIKWLevel` enum in `src/domain_models/types.py`.
2.  Define `NodeMetadata` in `src/domain_models/manifest.py` (or `types.py` if circular imports occur).
3.  Update `SummaryNode` to use `NodeMetadata` for its `metadata` field (or validate against it).

### Step 2: Extract Prompt Logic
1.  Create `src/matome/agents/strategies.py`.
2.  Define the `PromptStrategy` protocol.
3.  Copy the existing prompt templates from `SummarizationAgent` (or `constants.py`) into a new `BaseSummaryStrategy` class in `strategies.py`.

### Step 3: Refactor SummarizationAgent
1.  Modify `SummarizationAgent.__init__` or `summarize` to accept an optional `strategy: PromptStrategy`.
2.  If no strategy is provided, default to `BaseSummaryStrategy`.
3.  Replace the internal `_build_prompt` (or similar) method with a call to `strategy.create_prompt`.

### Step 4: Update RaptorEngine
1.  Ensure `RaptorEngine` instantiation of `SummarizationAgent` remains valid (it should work with the default).
2.  Verify that `RaptorEngine` propagates any necessary context (like tree level) if we decide to use it immediately (optional for this cycle, but good prep).

## 5. Test Strategy

### 5.1. Unit Testing
-   **Strategies:** Create a test `tests/agents/test_strategies.py`. Instantiate `BaseSummaryStrategy` and verify it produces the expected prompt string for a given input.
-   **Metadata:** Create a test `tests/domain_models/test_metadata.py`. Verify that `SummaryNode` correctly validates `dikw_level` and that invalid strings raise `ValidationError`.

### 5.2. Integration Testing
-   **Agent:** Test `SummarizationAgent` with a **Mock Strategy**. Inject a strategy that returns a fixed prompt "MOCK PROMPT" and verify the agent sends this exact string to the (mocked) LLM. This confirms the delegation is working.
-   **Pipeline:** Run the full `RaptorEngine` on a small text file. Inspect the `chunks.db` (or output objects) to ensure `SummaryNode` objects have the default `dikw_level="data"` (or whatever the default is).

### 5.3. Regression Testing
-   **Critical:** Run the existing test suite (`pytest`). **ALL TESTS MUST PASS.** If the refactoring breaks any existing test, it is a failure.
-   **Behavioral:** Run the CLI manually on a sample file and compare the output `summary.md` with a version generated before the changes. They should be identical (or semantically equivalent if randomness is involved).
