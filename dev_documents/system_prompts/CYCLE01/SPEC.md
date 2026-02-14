# Cycle 01 Specification: Core Architecture & DIKW Strategy Engine

## 1. Summary

This cycle lays the foundational logic for the Matome 2.0 "Knowledge Installation" system. The primary goal is to transition from a generic summarization tool to a sophisticated "Reverse-DIKW" generator. We will implement the "Prompt Strategy Pattern" to decouple summarization logic from the execution engine, enabling the system to generate distinct types of content: "Wisdom" (L1), "Knowledge" (L2), and "Information" (L3).

At the end of this cycle, the system will be able to ingest a raw text file and produce a hierarchical summary where each level serves a specific cognitive purpose—philosophical insight, structural understanding, or actionable advice—rather than just being a shorter version of the text. This is the critical backend engine that will power the interactive GUI in later cycles.

## 2. System Architecture

This cycle focuses on refactoring the `agents` and `engines` modules to support the new Strategy Pattern and address critical scalability issues.

### File Structure (ASCII Tree)

```
matome/
├── src/
│   ├── domain_models/
│   │   ├── manifest.py         # [Modify] Update SummaryNode to support typed metadata; Remove all_nodes from DocumentTree
│   │   ├── types.py            # [Modify] Add DIKWLevel Enum / Literals
│   │   ├── config.py           # [Modify] Add strategy_mapping to ProcessingConfig
│   │   └── constants.py        # [Modify] Add default prompt templates for each level
│   └── matome/
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── **strategies.py**   # [Create] New PromptStrategy abstract base & implementations
│       │   └── summarizer.py   # [Modify] Update to accept PromptStrategy
│       ├── engines/
│       │   ├── raptor.py       # [Modify] Update tree generation to use correct strategy per level & streaming
│       │   └── **interactive.py**  # [Create] Skeleton for future use (Cycle 02 prep)
│       ├── utils/
│       │   └── prompts.py      # [Modify] Store new DIKW prompt templates
│       └── cli.py              # [Modify] Add '--mode dikw' flag
```

### Key Components

1.  **PromptStrategy (New Interface):**
    Located in `src/matome/interfaces.py` (ABC) and implemented in `src/matome/agents/strategies.py`. This abstract base class defines how a prompt is constructed.
    -   `format_prompt(context, children_text)`: Returns the full prompt string.
    -   `parse_output(response)`: helper to clean up LLM output.

2.  **Concrete Strategies:**
    -   `WisdomStrategy`: For the root node. Prompt focuses on "one big idea," "aphorism," "philosophy."
    -   `KnowledgeStrategy`: For intermediate nodes. Prompt focuses on "mental models," "frameworks," "mechanisms."
    -   `InformationStrategy`: For leaf-adjacent nodes. Prompt focuses on "actionable steps," "checklists," "how-to."

3.  **SummarizationAgent (Refactored):**
    Located in `src/matome/agents/summarizer.py`.
    -   **Before:** `summarize(text, level)` -> logic inside.
    -   **After:** `summarize(text, strategy: PromptStrategy)` -> logic delegated.

4.  **RaptorEngine (Updated & Scalable):**
    Located in `src/matome/engines/raptor.py`.
    -   **Memory Safety (Critical):** Must use generators/iterators for ALL data processing (embedding, clustering, summarization). NEVER load all embeddings or all summary nodes into memory lists.
    -   **Strategy Selection:** Use `config.strategy_mapping` to determine strategy based on level.
    -   **Error Handling:** Implement `try/except` blocks with custom `MatomeError` exceptions for clustering and embedding failures.
    -   **Input Validation:** Validate `combined_text` length before summarization to prevent DoS.

## 3. Design Architecture

The design ensures strict typing and validation using Pydantic, even for metadata.

### Data Models

**1. DIKW Levels (Enumeration):**
Defined in `src/domain_models/types.py`.

```python
from enum import Enum

class DIKWLevel(str, Enum):
    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"
```

**2. NodeMetadata (Schema):**
We will enforce this schema on `SummaryNode.metadata`. Although `SummaryNode` accepts a generic `dict`, we will use a Pydantic model to validate it before assignment.

```python
class NodeMetadata(BaseModel):
    dikw_level: DIKWLevel
    is_user_edited: bool = False
    refinement_history: list[str] = Field(default_factory=list)
```

**3. ProcessingConfig (Update):**
Add `strategy_mapping` to allow dynamic configuration of strategies.

```python
class ProcessingConfig(BaseModel):
    # ... existing fields ...
    strategy_mapping: dict[DIKWLevel, str] = {
        DIKWLevel.WISDOM: "wisdom",
        DIKWLevel.KNOWLEDGE: "knowledge",
        DIKWLevel.INFORMATION: "information",
    }
```

**4. Prompt Strategy Interface:**

```python
from abc import ABC, abstractmethod

class PromptStrategy(ABC):
    @abstractmethod
    def format_prompt(self, children_text: list[str]) -> str:
        """Constructs the prompt for the LLM."""
        pass

    @property
    @abstractmethod
    def dikw_level(self) -> DIKWLevel:
        """Returns the target DIKW level."""
        pass
```

### Constraints & Invariants
-   **Level Assignment:** A node at Level 1 (summarizing chunks) is *always* `INFORMATION` by default. The Root Node is *always* `WISDOM`. Intermediate nodes are `KNOWLEDGE`.
-   **Output Length:** Wisdom nodes must be short (< 50 words). Information nodes must be structured (markdown lists).
-   **Statelessness:** Strategies must not store data. They are pure logic containers.
-   **Scalability:** The `DocumentTree` object MUST NOT contain `all_nodes` as a dictionary of all nodes if the dataset is large. It should rely on `DiskChunkStore` for retrieval. We will remove `all_nodes` from the `DocumentTree` model to enforce this.

## 4. Implementation Approach

1.  **Step 1: Define Constants & Types**
    -   Update `src/domain_models/types.py` with `DIKWLevel`.
    -   Add prompt templates to `src/matome/utils/prompts.py`.
    -   Update `src/domain_models/config.py`.

2.  **Step 2: Implement Strategies**
    -   Create `src/matome/agents/strategies.py`.
    -   Implement `WisdomStrategy`, `KnowledgeStrategy`, `InformationStrategy` classes.
    -   Ensure each class imports the correct prompt template.

3.  **Step 3: Refactor SummarizationAgent**
    -   Modify `SummarizationAgent` to accept an optional `strategy` argument in its `summarize` method.
    -   If no strategy is provided, default to a generic one (backward compatibility).

4.  **Step 4: Update RaptorEngine**
    -   Refactor `_process_level_zero` and `_embed_and_cluster_next_level` to be strictly streaming.
    -   In `_process_layer`, determine the current level.
    -   Instantiate the appropriate Strategy using `config.strategy_mapping`.
    -   Pass this strategy to the `SummarizationAgent`.
    -   When creating the `SummaryNode`, populate `metadata={'dikw_level': strategy.dikw_level}`.
    -   Add error handling and input validation.

5.  **Step 5: CLI Integration**
    -   Add `--mode dikw` to `matome.cli`.
    -   Ensure the runner utilizes the new logic when this flag is set.

## 5. Test Strategy

### Unit Testing Approach
-   **Test Case 1 (Wisdom):** Verify that `WisdomStrategy.format_prompt` includes keywords like "philosophy," "insight," "abstract."
-   **Test Case 2 (Information):** Verify that `InformationStrategy` includes instructions for "markdown checklists" and "actionable steps."
-   **Test Case 3 (Agent Integration):** Mock the LLM backend using `unittest.mock`. Pass a `WisdomStrategy` to `SummarizationAgent`. Assert that the agent sends the correct prompt to the mock LLM.
-   **Test Case 4 (Metadata Validation):** Create a `SummaryNode` with invalid metadata. Assert that Pydantic raises a validation error.
-   **Test Case 5 (Streaming):** Verify that `RaptorEngine` methods return generators and do not consume full lists.

### Integration Testing Approach
We will verify the flow from `RaptorEngine` down to the `DiskChunkStore`.
-   **Test Case 1 (End-to-End Generation):** Run the `matome` CLI with a small sample text (e.g., 2000 words). Use the `--mode dikw` flag.
-   **Verification:** Inspect the generated `chunks.db` (or output JSON).
    -   Check if the Root Node has `metadata.dikw_level == "wisdom"`.
    -   Check if Level 1 Nodes have `metadata.dikw_level == "information"`.
    -   Read the text of the Root Node. It should be short and abstract.
    -   Read the text of a Level 1 Node. It should be detailed and actionable.
