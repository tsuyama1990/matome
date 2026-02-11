# Cycle 02 Specification: DIKW Generation Engine

## 1. Summary

Cycle 02 focuses on the core value proposition of Matome 2.0: the ability to generate content that aligns with the DIKW (Data, Information, Knowledge, Wisdom) hierarchy. Having established the architectural foundation in Cycle 01 (Metadata and Strategy Pattern), we will now implement the specific logic required to produce "Semantic Zooming" content.

We will create three distinct concrete implementations of the `PromptStrategy` protocol:
1.  **`WisdomStrategy`**: Designed for the root node. It instructs the LLM to distill vast amounts of context into a single, profound aphorism or philosophical statement (20-40 characters).
2.  **`KnowledgeStrategy`**: Designed for intermediate nodes. It instructs the LLM to extract frameworks, mechanisms, and "Why" logic, avoiding mere fact listing.
3.  **`ActionStrategy`**: Designed for leaf/low-level nodes. It instructs the LLM to convert information into actionable checklists and "How-to" guides.

Additionally, we will upgrade the `RaptorEngine` to intelligently select the appropriate strategy based on the current depth of the tree being processed. This transforms the engine from a generic summarizer into a context-aware knowledge generator. By the end of this cycle, the CLI will support a new mode (e.g., `--mode dikw`) that produces a fully structured DIKW tree.

## 2. System Architecture

### 2.1. File Structure

```ascii
matome/
├── src/
│   ├── domain_models/
│   │   ├── constants.py
│   │   └── manifest.py
│   ├── matome/
│   │   ├── agents/
│   │   │   ├── **strategies.py** # MODIFY: Add Wisdom, Knowledge, Action strategies
│   │   │   └── summarizer.py
│   │   ├── engines/
│   │   │   └── **raptor.py**     # MODIFY: Add logic to switch strategies based on tree level
│   │   └── **cli.py**            # MODIFY: Add --mode argument
├── tests/
│   ├── unit/
│   │   └── **test_dikw_strategies.py** # CREATE: Test specific prompt outputs
│   └── integration/
│       └── test_dikw_generation.py
└── pyproject.toml
```

### 2.2. Component Details

#### `src/matome/agents/strategies.py` (Modification)
We will implement the following classes:
-   `WisdomStrategy`: Implements `create_prompt` with a focus on abstraction and brevity.
-   `KnowledgeStrategy`: Implements `create_prompt` with a focus on structure and mental models.
-   `ActionStrategy`: Implements `create_prompt` with a focus on executability (checklists).

#### `src/matome/engines/raptor.py` (Modification)
The `RaptorEngine` needs a logic update to determine which strategy to use.
-   **Current Logic**: Uniform summarization for all levels.
-   **New Logic**:
    -   **Leaf Nodes (Level 0)**: Use `ActionStrategy`.
    -   **Intermediate Nodes**: Use `KnowledgeStrategy`.
    -   **Root Node**: Use `WisdomStrategy`.
-   **Factory Method**: A helper `_get_strategy_for_level(level, max_depth)` will be added to encapsulate this logic.

#### `src/matome/cli.py` (Modification)
-   Add a `--mode` option to the `run` command.
-   Values: `default` (legacy behavior), `dikw` (new behavior).
-   Pass this configuration to the `RaptorEngine`.

## 3. Design Architecture

### 3.1. Strategy Definitions

The success of this cycle depends entirely on the quality of the prompt engineering within these strategies.

#### WisdomStrategy
-   **Goal**: The "Aha!" moment.
-   **Prompt Key Elements**:
    -   "Ignore details."
    -   "Identify the core philosophy."
    -   "Output a single sentence under 50 characters."
    -   "Use an imperative or declarative tone."
-   **Example Output**: "Systems thinking beats goal setting."

#### KnowledgeStrategy
-   **Goal**: Understanding the structure.
-   **Prompt Key Elements**:
    -   "Explain the *mechanism*."
    -   "Identify the framework."
    -   "Group concepts logically."
    -   "Explain *Why* this works."
-   **Example Output**:
    -   **Concept**: Anomaly Detection
    -   **Mechanism**: Comparing 15-year baselines.
    -   **Why**: Markets revert to mean over long periods.

#### ActionStrategy
-   **Goal**: Execution.
-   **Prompt Key Elements**:
    -   "Extract actionable steps."
    -   "Create a checklist."
    -   "Include specific criteria (numbers, dates)."
-   **Example Output**:
    -   [ ] Screen for stocks with PSR < 1.0.
    -   [ ] Verify self-capital ratio > 50%.

### 3.2. Engine Logic: The Level Mapping

The mapping logic must be dynamic because the tree height isn't known until runtime (in standard RAPTOR), though our implementation might force a specific structure or adapt dynamically.

Assuming a bottom-up approach:
-   **Level 0 (Leaves)**: Always `ActionStrategy` (or `InformationStrategy`).
-   **Level 1 to Max-1**: `KnowledgeStrategy`.
-   **Final Level (Root)**: `WisdomStrategy`.

*Design Note*: Since RAPTOR builds levels iteratively, we might not know if the *current* level is the *final* level until the loop finishes.
*Refinement*: We can implement a post-processing step for the Root Node, or (simpler for now) apply `KnowledgeStrategy` to all intermediate levels and `ActionStrategy` to leaves. The Root Node can be explicitly re-summarized with `WisdomStrategy` at the very end of the process.

## 4. Implementation Approach

### Step 1: Implement Strategies (`src/matome/agents/strategies.py`)
1.  Implement `ActionStrategy`.
    -   Prompt: "You are an operations manager. Convert this text into a checklist..."
2.  Implement `KnowledgeStrategy`.
    -   Prompt: "You are a systems architect. Map out the mental models..."
3.  Implement `WisdomStrategy`.
    -   Prompt: "You are a philosopher. Summarize the essence in one sentence..."

### Step 2: Refactor `RaptorEngine` (`src/matome/engines/raptor.py`)
1.  Modify `__init__` to accept a `mode` string (default="default").
2.  In the `run()` loop (or equivalent recursive method):
    -   Identify the current level index.
    -   Instantiate the appropriate strategy.
    -   Pass this strategy to the `SummarizationAgent`.
3.  **Special Handling for Root**:
    -   Since standard RAPTOR reduces until one node remains, ensure that the *final* reduction uses the `WisdomStrategy`.
    -   Alternatively, re-process the final root node with `WisdomStrategy` to overwrite its generic summary.

### Step 3: CLI Update (`src/matome/cli.py`)
1.  Update `typer` arguments to accept `--mode`.
2.  Propagate this flag to `ProcessingConfig` or directly to the engine.

## 5. Test Strategy

### 5.1. Unit Testing Approach (Min 300 words)
We need to verify that each strategy produces the correct *type* of output. Since we can't deterministically test LLM output, we will mock the LLM but check the *prompt construction*.

**`tests/unit/test_dikw_strategies.py`**:
-   **Test Case 1: Wisdom Prompt**: Instantiate `WisdomStrategy`. Call `create_prompt`. Assert the returned string contains keywords like "philosophy", "essence", "one sentence".
-   **Test Case 2: Knowledge Prompt**: Instantiate `KnowledgeStrategy`. Call `create_prompt`. Assert keywords like "framework", "mechanism", "structure".
-   **Test Case 3: Action Prompt**: Instantiate `ActionStrategy`. Call `create_prompt`. Assert keywords like "checklist", "actionable", "steps".
-   **Test Case 4: Parsing**: If specific parsing logic is added (e.g., stripping Markdown code blocks), test it with various raw string inputs.

### 5.2. Integration Testing Approach (Min 300 words)
Integration tests will verify the engine's ability to switch strategies dynamically.

**`tests/integration/test_dikw_flow.py`**:
-   **Test Case 1: Strategy Switching**:
    -   Mock `SummarizationAgent` to return a string that echoes the strategy name (e.g., "[WISDOM] ...").
    -   Run `RaptorEngine` with `--mode dikw`.
    -   Inspect the resulting `DocumentTree`.
    -   Assert that Leaf Nodes contain "[ACTION]" (or correspond to Level 0).
    -   Assert that Intermediate Nodes contain "[KNOWLEDGE]".
    -   Assert that the Root Node contains "[WISDOM]".
    -   Assert that the `dikw_level` metadata field is correctly set for each node type (this requires the engine to also set the metadata when saving, which should be part of the implementation step).

**`tests/integration/test_cli_mode.py`**:
-   **Test Case 1**: Run the CLI with `--mode dikw`. Verify it runs without error.
-   **Test Case 2**: Run with `--mode default`. Verify it mimics legacy behavior.
