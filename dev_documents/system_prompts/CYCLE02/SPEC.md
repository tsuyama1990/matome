# Cycle 02 Specification: DIKW Engine Implementation

## 1. Summary

Cycle 02 focuses on implementing the core logic for the **Data-Information-Knowledge-Wisdom (DIKW)** hierarchy. Building on the `PromptStrategy` pattern established in Cycle 01, we will implement three distinct strategies (`WisdomStrategy`, `KnowledgeStrategy`, `InformationStrategy`) that enforce the semantic rules defined in the requirements. Furthermore, we will update the `RaptorEngine` and CLI to support a new execution mode (`--mode dikw`) that utilizes these strategies to generate a structured knowledge tree.

## 2. System Architecture

```ascii
src/matome/
├── agents/
│   ├── **strategies.py**       # Modified: Add Wisdom, Knowledge, Information strategies
│   └── summarizer.py
├── engines/
│   └── **raptor.py**           # Modified: Add logic to switch strategy based on level
├── **cli.py**                  # Modified: Add --mode argument
└── ...
```

### Key Changes
1.  **`src/matome/agents/strategies.py`**: Implementation of `WisdomStrategy`, `KnowledgeStrategy`, `InformationStrategy`.
2.  **`src/matome/engines/raptor.py`**:
    *   Currently, `RaptorEngine` likely uses a single `SummarizationAgent` instance.
    *   We will modify it to accept a `mode` (default or dikw).
    *   If `mode="dikw"`, the engine must instantiate or configure the agent with the correct strategy *per level*.
    *   **Logic:**
        *   Level 0 (Leaf clusters) -> `InformationStrategy` (to generate L3)
        *   Level 1 (Clusters of L3) -> `KnowledgeStrategy` (to generate L2)
        *   Level 2 (Root) -> `WisdomStrategy` (to generate L1)
    *   *Note on Levels:* The RAPTOR algorithm builds bottom-up. Level 0 corresponds to the first abstraction layer (L3 Information). Level 1 is the next (L2 Knowledge). The final root node is L1 Wisdom.
3.  **`src/matome/cli.py`**: Add `mode: str = "default"` to the `run` command.

## 3. Design Architecture

### 3.1. DIKW Strategies

Each strategy implements `PromptStrategy` with specific prompt engineering.

**`WisdomStrategy` (L1)**
*   **Prompt Goal:** Extract a single profound truth/aphorism (20-50 chars).
*   **Constraint:** Must be abstract, philosophical, and memorable. No specific data points.

**`KnowledgeStrategy` (L2)**
*   **Prompt Goal:** Explain the *mental model* or *mechanism* (Why/How).
*   **Constraint:** Structured explanation of the logic underpinning the Wisdom.

**`InformationStrategy` (L3)**
*   **Prompt Goal:** Create an actionable checklist or set of rules (What to do).
*   **Constraint:** Must be immediately executable by the user.

### 3.2. Engine Logic (Level Mapping)

The `RaptorEngine` processes clusters layer by layer. We need a mapping mechanism.

```python
# Conceptual logic in RaptorEngine.run_level()
current_level_index = ... # 0, 1, 2...

if self.mode == "dikw":
    if current_level_index == 0:
        strategy = InformationStrategy()
        target_dikw = DIKWLevel.INFORMATION
    elif current_level_index == 1:
        strategy = KnowledgeStrategy()
        target_dikw = DIKWLevel.KNOWLEDGE
    else:
        strategy = WisdomStrategy()
        target_dikw = DIKWLevel.WISDOM
else:
    strategy = BaseSummaryStrategy()
    target_dikw = DIKWLevel.DATA

# Agent execution
summary_text = self.agent.summarize(cluster_text, strategy=strategy)

# Node Creation
node = SummaryNode(..., metadata=NodeMetadata(dikw_level=target_dikw))
```

*Note:* The number of levels in RAPTOR is dynamic based on text length. We may need to force a specific depth or adapt the mapping (e.g., "Top level is always Wisdom", "Bottom level is always Information", "Middle are Knowledge"). For MVP, we can assume a standard 3-layer depth or apply heuristics (Top=Wisdom, Bottom=Information, All Intermediate=Knowledge).

**Decision:**
*   **Root:** Wisdom
*   **Leaves (Summaries of chunks):** Information
*   **Intermediate:** Knowledge

## 4. Implementation Approach

### Step 1: Implement Strategies
In `src/matome/agents/strategies.py`, implement the three classes. Use the prompts defined in `ALL_SPEC.md` as the template.

### Step 2: Refactor RaptorEngine
Modify `src/matome/engines/raptor.py`.
*   Add `mode` parameter to `__init__`.
*   In the loop where it processes levels, verify the current depth.
*   Implement the mapping logic (Root/Intermediate/Leaf) to select the correct strategy.
*   Instantiate the `SummarizationAgent` with the selected strategy (or pass it to the `summarize` method if the agent is shared).
*   Ensure the created `SummaryNode` gets the correct `dikw_level` in its metadata.

### Step 3: Update CLI
Modify `src/matome/cli.py` to accept `--mode` argument (enum: `default`, `dikw`). Pass this to the engine.

### Step 4: Verify
Run the CLI with `--mode dikw` on a sample file and inspect the database.

## 5. Test Strategy

### 5.1. Unit Testing
*   **`tests/test_strategies_dikw.py`**:
    *   Test each strategy's `format_prompt` to ensure it contains the correct keywords (e.g., "aphorism", "mental model", "checklist").
*   **`tests/test_raptor_dikw.py`**:
    *   Mock `SummarizationAgent`.
    *   Run `RaptorEngine` in `dikw` mode with a mock clustering result that produces 3 levels.
    *   Verify that `SummarizationAgent.summarize` is called with `InformationStrategy` for the first pass, `KnowledgeStrategy` for the second, and `WisdomStrategy` for the final pass.

### 5.2. Integration Testing
*   **`tests/test_cli_dikw.py`**:
    *   Run `matome run test.txt --mode dikw`.
    *   Load the resulting `chunks.db`.
    *   Query nodes where `dikw_level='wisdom'`. Assert count > 0.
    *   Query nodes where `dikw_level='information'`. Assert count > 0.
