# Cycle 01: Core Refactoring & Strategy Pattern

## 1. Summary

The primary goal of Cycle 01 is to lay the architectural foundation for the **DIKW (Data, Information, Knowledge, Wisdom)** hierarchy generation. Currently, the `SummarizationAgent` uses a hardcoded prompt logic suitable for generic summarization. To support "Semantic Zooming," we need to generate different types of summaries based on the tree level (Wisdom at the root, Knowledge in the middle, Information at the leaves).

We will implement the **Strategy Pattern** to decouple the prompt construction logic from the agent itself. This allows us to inject specific behavior (e.g., "Be philosophical" vs. "Be actionable") without cluttering the agent code with conditional logic. Additionally, we will update the `SummaryNode` schema to support the new metadata required for tracking these abstraction levels.

## 2. System Architecture

We will introduce a new module for strategies and refactor the existing agent.

### File Structure
```
src/
├── domain_models/
│   └── **manifest.py**       # Modify: Add DIKWLevel enum and update NodeMetadata
└── matome/
    ├── agents/
    │   ├── **strategies.py** # Create: Define PromptStrategy and implementations
    │   └── **summarizer.py** # Modify: Update SummarizationAgent to use strategies
    └── **interfaces.py**     # Create/Modify: Define Protocol for strategies
```

**Bold** files are to be created or modified in this cycle.

## 3. Design Architecture

### 3.1. Domain Models (`src/domain_models/manifest.py`)

We need to formalize the DIKW levels and track user interactions.

```python
from enum import StrEnum
from pydantic import BaseModel, Field

class DIKWLevel(StrEnum):
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"

class NodeMetadata(BaseModel):
    # Existing fields...
    dikw_level: DIKWLevel | None = None
    is_user_edited: bool = False
    refinement_history: list[str] = Field(default_factory=list)
```

### 3.2. Prompt Strategy (`src/matome/agents/strategies.py`)

We will define a protocol `PromptStrategy` and implement four concrete strategies.

**Protocol Definition:**
```python
from typing import Protocol

class PromptStrategy(Protocol):
    def format_prompt(self, text: str, existing_summary: str | None = None) -> str:
        ...
```

**Concrete Implementations:**

1.  **`BaseSummaryStrategy`**: The existing "Chain of Density" or standard summarization logic. Used as a default.
2.  **`WisdomStrategy` (L1)**:
    - **Goal**: Extract the philosophical core.
    - **Constraint**: Output must be 20-50 characters. No bullet points. Abstract concepts only.
    - **Prompt**: "Distill the following text into a single, profound aphorism or truth..."
3.  **`KnowledgeStrategy` (L2)**:
    - **Goal**: Explain mechanisms and frameworks.
    - **Constraint**: Focus on "Why" and "How it works." Group concepts into structural pillars.
    - **Prompt**: "Identify the underlying mental models or frameworks in the text..."
4.  **`InformationStrategy` (L3)**:
    - **Goal**: Actionable items.
    - **Constraint**: "How-to", Checklists, specific steps.
    - **Prompt**: "Convert this text into a concrete action plan or checklist..."

### 3.3. Summarization Agent (`src/matome/agents/summarizer.py`)

The agent will be updated to accept an optional strategy in its `summarize` method.

```python
class SummarizationAgent:
    def summarize(self, text: str, strategy: PromptStrategy | None = None) -> str:
        # If no strategy is provided, use a default (BaseSummaryStrategy)
        strategy = strategy or BaseSummaryStrategy()
        prompt = strategy.format_prompt(text)
        # ... call LLM with prompt ...
```

## 4. Implementation Approach

1.  **Update Schema**:
    - Modify `src/domain_models/manifest.py` to include `DIKWLevel` and updated `NodeMetadata`.
    - Ensure backward compatibility (fields should be optional or have defaults).

2.  **Define Protocol**:
    - Create `src/matome/interfaces.py` (if not exists) or `strategies.py` and define `PromptStrategy`.

3.  **Implement Strategies**:
    - Create `src/matome/agents/strategies.py`.
    - Implement `BaseSummaryStrategy` (porting existing logic).
    - Implement `WisdomStrategy`, `KnowledgeStrategy`, `InformationStrategy` with distinct prompts.

4.  **Refactor Agent**:
    - Modify `SummarizationAgent` to import and use the strategies.
    - Update the `summarize` signature.

5.  **Verify**:
    - Run existing tests to ensure no regression (default behavior should remain the same).

## 5. Test Strategy

### Unit Testing
- **Strategy Tests**:
    - Create `tests/unit/test_strategies.py`.
    - Test `WisdomStrategy.format_prompt()`: Ensure the output string contains key constraints (e.g., "aphorism", "20-50 characters").
    - Test `KnowledgeStrategy` and `InformationStrategy` prompts similarly.
- **Schema Tests**:
    - Create `tests/unit/test_store_schema.py` or similar.
    - Verify `NodeMetadata` accepts valid `DIKWLevel` values.
    - Verify validation fails for invalid levels.

### Integration Testing
- **Agent Integration**:
    - Create `tests/integration/test_agent_strategies.py`.
    - Mock the LLM call.
    - Instantiate `SummarizationAgent`.
    - Call `summarize(text, strategy=WisdomStrategy())`.
    - Verify that the mocked LLM receives the correct prompt associated with the Wisdom strategy.
