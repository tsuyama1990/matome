# Cycle 01 Specification: Core Refactoring & DIKW Metadata

## 1. Summary

The primary objective of Cycle 01 is to establish the foundational data structures and architectural patterns required to support the Matome 2.0 "Knowledge Installation" update. The current system operates on a relatively simple model where `SummaryNode` objects contain text and basic metadata, and the `SummarizationAgent` contains hardcoded logic for generating summaries. This structure, while functional for a CLI tool, is insufficient for the complex, interactive, and hierarchical requirements of the new Semantic Zooming capability.

In this cycle, we will introduce the **DIKW (Data, Information, Knowledge, Wisdom)** hierarchy into the domain model without breaking the existing database schema. We will achieve this by defining a robust `NodeMetadata` schema using Pydantic, which will be embedded within the existing `SummaryNode`. This approach allows us to "tag" each node with its abstraction level (`wisdom`, `knowledge`, `information`, `data`) and track its refinement history (`is_user_edited`), enabling the future GUI to treat nodes differently based on their type.

Furthermore, we will decouple the prompt generation logic from the `SummarizationAgent` by introducing the **Prompt Strategy Pattern**. Currently, the prompt engineering is tightly coupled with the agent's execution logic. By defining a `PromptStrategy` protocol (interface), we pave the way for Cycle 02, where we will implement specific strategies for generating Wisdom, Knowledge, and Action. For this cycle, our goal is to define the interface and ensure the `SummarizationAgent` can accept and utilize a strategy object.

This cycle is purely infrastructural. There are no user-facing feature changes, and the CLI behavior should remain identical (or technically "neutral") after these changes. The success of this cycle is measured by the successful integration of the new metadata schema and the ability to instantiate a `SummarizationAgent` with a (dummy or basic) strategy, verified through rigorous unit testing. This sets the stage for the implementation of the actual generation logic in Cycle 02 and the interactive engine in Cycle 03.

## 2. System Architecture

This section details the file structure and the specific components that will be created or modified. The focus is on the `src/domain_models` and `src/matome/agents` directories.

### 2.1. File Structure

The following ASCII tree depicts the file structure for this cycle. Files marked in **bold** are to be created or significantly modified.

```ascii
matome/
├── src/
│   ├── domain_models/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── **manifest.py**       # MODIFY: Update SummaryNode to use NodeMetadata
│   │   └── **metadata.py**       # CREATE: Define DIKWLevel and NodeMetadata
│   ├── matome/
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── **strategies.py** # CREATE: Define PromptStrategy Protocol
│   │   │   └── **summarizer.py** # MODIFY: Inject PromptStrategy into Agent
│   │   ├── engines/
│   │   │   ├── __init__.py
│   │   │   └── raptor.py
│   │   ├── utils/
│   │   │   └── store.py
│   │   └── cli.py
├── tests/
│   ├── unit/
│   │   ├── **test_metadata.py**  # CREATE: Test metadata validation
│   │   └── **test_strategies.py**# CREATE: Test strategy injection
│   └── integration/
│       └── test_pipeline_refactor.py
└── pyproject.toml
```

### 2.2. Component Details

#### `src/domain_models/metadata.py` (New)
This file will act as the single source of truth for the node metadata schema. By isolating this logic, we prevent circular dependencies and keep `manifest.py` clean.
-   **Classes**:
    -   `DIKWLevel` (Enum): Defines the four levels of the hierarchy.
    -   `NodeMetadata` (Pydantic Model): Validates the metadata dictionary.

#### `src/domain_models/manifest.py` (Modification)
The `SummaryNode` class currently uses a generic `metadata: dict = Field(default_factory=dict)`. We will strictly type this field while maintaining backward compatibility for deserialization.
-   **Changes**:
    -   Import `NodeMetadata` from `metadata.py`.
    -   Update `metadata` field type to `NodeMetadata`.
    -   Add validators to ensure legacy dictionaries are correctly converted to `NodeMetadata` objects during loading from the DB.

#### `src/matome/agents/strategies.py` (New)
This file defines the contract for prompt strategies. It allows the `SummarizationAgent` to be agnostic of *how* a prompt is built.
-   **Classes**:
    -   `PromptStrategy` (Protocol): Defines `create_prompt` and `parse_output` methods.
    -   `BaseSummaryStrategy` (Concrete Class): A default implementation that mimics the current "generic summary" logic, ensuring the system remains functional during the transition.

#### `src/matome/agents/summarizer.py` (Modification)
The agent will be refactored to rely on the strategy.
-   **Changes**:
    -   `__init__` will accept an optional `prompt_strategy: PromptStrategy`.
    -   If no strategy is provided, it defaults to `BaseSummaryStrategy`.
    -   The `summarize` method will replace its hardcoded f-string prompt construction with `self.prompt_strategy.create_prompt(...)`.

## 3. Design Architecture

This section serves as the pre-implementation design document, focusing on the Pydantic schemas and interface contracts.

### 3.1. Domain Concepts: The DIKW Hierarchy

The core concept introduced in this cycle is the `DIKWLevel`. We explicitly define this as a string-based Enum to ensure serialization compatibility with JSON and SQLite.

```python
from enum import Enum

class DIKWLevel(str, Enum):
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"
```

**Constraints**:
-   The system MUST NOT accept any string other than these four values for the `dikw_level` field.
-   Comparison logic (e.g., `level > DIKWLevel.DATA`) might be needed, so implementing `__lt__` based on a hierarchy index is recommended.

### 3.2. Data Model: NodeMetadata

The `NodeMetadata` model is designed to be extensible. While we focus on DIKW today, we anticipate future needs like "edit history" or "source verification status."

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class NodeMetadata(BaseModel):
    dikw_level: DIKWLevel = Field(
        default=DIKWLevel.DATA,
        description="The abstraction level of this node."
    )
    is_user_edited: bool = Field(
        default=False,
        description="True if the user has manually refined this node."
    )
    refinement_history: List[str] = Field(
        default_factory=list,
        description="List of user instructions applied to this node."
    )
    # Allow extra fields for backward compatibility with existing unstructured metadata
    model_config = {"extra": "allow"}
```

**Validation Rules**:
-   `dikw_level` defaults to `DATA` if missing (safe assumption for leaf nodes, though strictly root nodes should be Wisdom).
-   `is_user_edited` is critical for Cycle 03 (Interactive Engine). We define it now to ensure the schema is ready.

### 3.3. Interface: PromptStrategy

The `PromptStrategy` utilizes Python's `typing.Protocol` for structural subtyping. This is preferred over abstract base classes (ABC) for cleaner dependency injection and easier testing (mocking).

```python
from typing import Protocol, List

class PromptStrategy(Protocol):
    """
    Defines the contract for generating prompts and parsing responses
    for a specific DIKW level.
    """

    def create_prompt(self, context_chunks: List[str], current_level: int) -> str:
        """
        Constructs the LLM prompt based on the context and tree level.
        """
        ...

    def parse_output(self, llm_output: str) -> str:
        """
        Parses the raw LLM output into the final summary string.
        Useful for stripping "Here is the summary:" prefixes.
        """
        ...
```

**Consumers**: `SummarizationAgent` is the sole consumer of this interface.
**Producers**: In Cycle 02, we will produce `WisdomStrategy`, `KnowledgeStrategy`, etc. In Cycle 01, we produce `BaseSummaryStrategy`.

## 4. Implementation Approach

The implementation will proceed in a strict bottom-up order to prevent import errors and ensure testability at each step.

### Step 1: Implement `src/domain_models/metadata.py`
1.  Create the file.
2.  Define `DIKWLevel` Enum.
3.  Define `NodeMetadata` Pydantic model.
4.  Add a `model_validator` to `NodeMetadata` if sophisticated migration logic (e.g., inferring level from old keys) is needed, though simple defaults should suffice for now.

### Step 2: Refactor `src/domain_models/manifest.py`
1.  Import `NodeMetadata`.
2.  Locate `SummaryNode`.
3.  Change `metadata: Dict[str, Any]` to `metadata: NodeMetadata`.
4.  **Crucial**: Add a `pre`-validator using `@field_validator(mode='before')` to handle cases where `metadata` is loaded as a raw dict from JSON/DB. This validator should instantiate `NodeMetadata(**value)` if `value` is a dict.

### Step 3: Implement `src/matome/agents/strategies.py`
1.  Create the file.
2.  Define the `PromptStrategy` Protocol.
3.  Implement `BaseSummaryStrategy`.
    -   Copy the *existing* prompt logic from `SummarizationAgent` into `BaseSummaryStrategy.create_prompt`.
    -   Implement a passthrough `parse_output` (returns the string as-is).

### Step 4: Refactor `src/matome/agents/summarizer.py`
1.  Update `SummarizationAgent.__init__`.
    -   Add `prompt_strategy: Optional[PromptStrategy] = None`.
    -   Set `self.prompt_strategy = prompt_strategy or BaseSummaryStrategy()`.
2.  Update `SummarizationAgent.summarize`.
    -   Replace the hardcoded prompt generation with `prompt = self.prompt_strategy.create_prompt(context, level)`.
    -   Wrap the LLM call result with `self.prompt_strategy.parse_output(result)`.

### Step 5: Verification
1.  Run the existing test suite (`pytest`).
2.  If any existing tests mock `SummarizationAgent`, they might fail due to signature changes. Update them to be compatible.

## 5. Test Strategy

### 5.1. Unit Testing Approach (Min 300 words)
Unit tests for this cycle must focus on schema validation and interface adherence. Since we are changing the core data structures, we need to ensure that invalid data is rejected and valid data is correctly typed.

**`tests/unit/test_metadata.py`**:
-   **Test Case 1: Valid Instantiation**: Create `NodeMetadata` with valid DIKW levels. Assert that fields are correctly populated.
-   **Test Case 2: Invalid Level**: Attempt to create `NodeMetadata` with `dikw_level="super_wisdom"`. Assert that a `ValidationError` is raised. This ensures the Enum constraint is working.
-   **Test Case 3: Default Values**: Create `NodeMetadata` with an empty dict (or no arguments). Assert that `dikw_level` defaults to `DATA` and `is_user_edited` is `False`.
-   **Test Case 4: Extra Fields**: Pass extra keys like `{"source": "wiki"}`. Assert that they are preserved (due to `extra="allow"`), which is vital for backward compatibility.

**`tests/unit/test_manifest_integration.py`**:
-   **Test Case 1: SummaryNode Integration**: Create a `SummaryNode` passing a raw dict `{"dikw_level": "wisdom"}` to the `metadata` argument. Assert that `node.metadata` becomes an instance of `NodeMetadata`, proving the pre-validator works.

**`tests/unit/test_strategies.py`**:
-   **Test Case 1: Base Strategy Logic**: Instantiate `BaseSummaryStrategy`. Call `create_prompt` with sample chunks. Assert the output string matches the expected legacy prompt format.

### 5.2. Integration Testing Approach (Min 300 words)
Integration tests should verify that the refactored components work together within the larger system context. We need to ensure that the `SummarizationAgent`, when equipped with a strategy, can effectively drive the LLM (or a mock) and produce a result that fits into the `SummaryNode`.

**`tests/integration/test_agent_strategy_wiring.py`**:
-   **Test Case 1: Dependency Injection**: Instantiate `SummarizationAgent` with a custom `MockStrategy` (a simple class implementing the Protocol). Call `agent.summarize`. Assert that the agent calls `MockStrategy.create_prompt`. This verifies the wiring is correct and the agent is no longer using hardcoded logic.
-   **Test Case 2: End-to-End Node Creation**:
    1.  Create a `SummarizationAgent` with `BaseSummaryStrategy`.
    2.  Mock the LLM response.
    3.  Run `agent.summarize`.
    4.  Create a `SummaryNode` using the result.
    5.  Assert the node is valid and contains the default metadata.

**`tests/integration/test_backward_compatibility.py`**:
-   **Test Case 1: Loading Old Data**: Create a dummy JSON representing an "old" `SummaryNode` (without DIKW fields). Use `SummaryNode.model_validate_json` to load it. Assert that it loads successfully and `metadata.dikw_level` is set to the default `DATA`. This confirms that we haven't broken the ability to read existing databases.
