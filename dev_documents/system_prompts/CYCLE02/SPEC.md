# Cycle 02 Specification: DIKW Engine Implementation

## 1. Summary

Cycle 02 focuses on implementing the core logic for **Semantic Zooming**: the DIKW (Data, Information, Knowledge, Wisdom) hierarchy. We will leverage the `PromptStrategy` pattern established in Cycle 01 to create specific strategies for generating Wisdom, Knowledge, and Information summaries. Additionally, we will update the data schema to store DIKW metadata, enabling the system to distinguish between different levels of abstraction. This cycle transforms the generic summarizer into a specialized engine capable of extracting deep insights and actionable steps.

## 2. System Architecture

We will implement three new strategies and modify the data schema and CLI.

```ascii
src/
├── domain_models/
│   └── data_schema.py       # [MODIFIED] Add DIKW Metadata
├── matome/
│   ├── agents/
│   │   ├── strategies.py    # [MODIFIED] Implement DIKW Strategies
│   └── cli.py               # [MODIFIED] Add --mode argument
```

**New Classes:**
- **`WisdomStrategy`**: Specialized for profound, concise insights.
- **`KnowledgeStrategy`**: Specialized for structural understanding.
- **`InformationStrategy`**: Specialized for actionable checklists.

**Modified Classes:**
- **`NodeMetadata`**: Enriched with `dikw_level`, `refinement_history`, etc.
- **`SummarizationAgent`**: Updated to handle the metadata dictionary returned by the new strategies.
- **`matome.cli`**: Updated to accept `--mode` and instantiate the appropriate strategy.

## 3. Design Architecture

### 3.1. Data Models (Pydantic)

We will use `StrEnum` for type safety and extend the `NodeMetadata` model.

**`src/domain_models/data_schema.py`**

```python
from enum import StrEnum
from pydantic import BaseModel, Field
from typing import List, Optional

class DIKWLevel(StrEnum):
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"

class NodeMetadata(BaseModel):
    # Existing fields...
    dikw_level: DIKWLevel = Field(default=DIKWLevel.DATA)
    refinement_history: List[str] = Field(default_factory=list)
    is_user_edited: bool = Field(default=False)
```

### 3.2. Strategy Implementations

Each strategy implements `PromptStrategy` and defines a unique prompt template and parsing logic.

**`src/matome/agents/strategies.py`**

**WisdomStrategy**
- **Goal:** Extract the single most profound truth (L1).
- **Prompt Focus:** "Identify the core philosophical insight or 'One Big Idea'. Distill it into a single, punchy aphorism (20-40 chars). Do not use specific names or dates."
- **Output Constraint:** The summary must be extremely short.
- **Parsing:** Returns `{"summary": "...", "metadata": {"dikw_level": "wisdom"}}`.

**KnowledgeStrategy**
- **Goal:** Explain the underlying mechanisms (L2).
- **Prompt Focus:** "Explain the mental models, frameworks, or causal relationships ('Why' and 'How'). Structure the output as key concepts."
- **Output Constraint:** Structured text (markdown headers/bullets).
- **Parsing:** Returns `{"summary": "...", "metadata": {"dikw_level": "knowledge"}}`.

**InformationStrategy**
- **Goal:** Extract actionable steps (L3).
- **Prompt Focus:** "Extract actionable advice, checklists, or procedures ('What to do'). Format as a markdown checklist."
- **Output Constraint:** Markdown list (e.g., `- [ ] Do X`).
- **Parsing:** Returns `{"summary": "...", "metadata": {"dikw_level": "information"}}`.

### 3.3. Parsing Logic
Unlike the `BaseSummaryStrategy` which just returns a string, these strategies must return a dictionary that includes metadata. The `SummarizationAgent` (refactored in Cycle 01) is already set up to accept this dictionary and use it to populate the `SummaryNode`.
- **Constraint:** The parsing method must ensure that the returned dictionary keys align with the `SummaryNode` fields (specifically `metadata`).

## 4. Implementation Approach

This cycle requires careful attention to prompt engineering and data validation.

### Step 1: Update Data Schema
In `src/domain_models/data_schema.py`, define `DIKWLevel` using `StrEnum` (available in Python 3.11+). Update `NodeMetadata` to include the new fields with appropriate defaults to ensure backward compatibility for existing databases.

### Step 2: Implement WisdomStrategy
In `src/matome/agents/strategies.py`, create the class.
- **Prompt:** "You are a philosopher. Read the text and output ONE sentence capturing the deepest truth..."
- **Parse:** Return the summary and set `metadata.dikw_level = DIKWLevel.WISDOM`.

### Step 3: Implement KnowledgeStrategy
In `src/matome/agents/strategies.py`, create the class.
- **Prompt:** "You are a professor. explain the structural logic..."
- **Parse:** Return the summary and set `metadata.dikw_level = DIKWLevel.KNOWLEDGE`.

### Step 4: Implement InformationStrategy
In `src/matome/agents/strategies.py`, create the class.
- **Prompt:** "You are a tactical advisor. List actionable steps..."
- **Parse:** Return the summary and set `metadata.dikw_level = DIKWLevel.INFORMATION`.

### Step 5: CLI Integration
Update `src/matome/cli.py`.
- Add a `--mode` argument (choices: wisdom, knowledge, information, default).
- In the `run` command, switch on the mode string:
    - "wisdom" -> `strategy = WisdomStrategy()`
    - "knowledge" -> `strategy = KnowledgeStrategy()`
    - ...
- Pass the selected strategy to the `SummarizationAgent`.

## 5. Test Strategy

Testing focuses on ensuring that each strategy produces the correct *type* of content and correct metadata.

### 5.1. Unit Testing
**File:** `tests/agents/test_dikw_strategies.py`
- **Test Case 1: Wisdom Constraints**
    - **Input:** A long text.
    - **Action:** Call `WisdomStrategy().format_prompt(text)`.
    - **Assertion:** Prompt contains keywords like "aphorism" or "short".
- **Test Case 2: Metadata Injection**
    - **Input:** "Some text."
    - **Action:** Call `WisdomStrategy().parse_output("Life is suffering.")`.
    - **Assertion:** Returns `{'summary': 'Life is suffering.', 'metadata': {'dikw_level': 'wisdom'}}`.
- **Test Case 3: Information Formatting**
    - **Input:** "Do A then B."
    - **Action:** Call `InformationStrategy().format_prompt(...)`.
    - **Assertion:** Prompt requests a checklist format.

### 5.2. Integration Testing
**File:** `tests/agents/test_dikw_pipeline.py`
- **Test Case 1: End-to-End Generation**
    - **Setup:** Mock LLM to return specific strings based on prompt content.
    - **Action:** Run `SummarizationAgent` with `KnowledgeStrategy`.
    - **Assertion:** The resulting `SummaryNode` has `dikw_level=KNOWLEDGE` in its metadata.
- **Test Case 2: CLI Argument**
    - **Setup:** Invoke the CLI with `--mode wisdom`.
    - **Assertion:** The agent is initialized with `WisdomStrategy`.

### 5.3. Validation
Manually inspect the output of a real run (using `uv run matome run ...`) to ensure the prompts are effective. Adjust prompt wording if the "Wisdom" is too long or "Information" is not actionable.
