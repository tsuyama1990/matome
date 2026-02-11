# Cycle 02: DIKW Generation Engine

## 1. Summary

In this cycle, we will implement the core logic for the **DIKW Generation Engine**. Building upon the Strategy Pattern implemented in Cycle 01, we will modify the `RaptorEngine` to intelligently apply different strategies based on the level of the summary tree.

The goal is to enable a new processing mode (`--mode dikw`) that, instead of producing generic summaries at all levels, produces:
- **Information (L3)** at the leaf level (summarizing raw data chunks).
- **Knowledge (L2)** at intermediate levels (synthesizing information into frameworks).
- **Wisdom (L1)** at the root level (distilling knowledge into a core truth).

## 2. System Architecture

We will modify the engine and configuration to support mode switching.

### File Structure
```
src/
├── domain_models/
│   └── **config.py**          # Modify: Add ProcessingMode enum and config field
└── matome/
    ├── **cli.py**             # Modify: Add --mode argument
    └── engines/
        └── **raptor.py**      # Modify: Implement level-based strategy selection
```

## 3. Design Architecture

### 3.1. Processing Configuration (`src/domain_models/config.py`)

We introduce a `ProcessingMode` enum to control the engine's behavior.

```python
from enum import StrEnum

class ProcessingMode(StrEnum):
    DEFAULT = "default"  # Standard RAPTOR summarization
    DIKW = "dikw"        # DIKW hierarchical generation

class ProcessingConfig(BaseModel):
    # Existing fields...
    processing_mode: ProcessingMode = ProcessingMode.DEFAULT
```

### 3.2. Raptor Engine Logic (`src/matome/engines/raptor.py`)

The `RaptorEngine` currently iterates through levels of the tree. We will inject logic to select the appropriate `PromptStrategy` based on the current level and the `processing_mode`.

**Logic Flow:**
1.  **Level 0 (Cluster Summaries from Chunks)**:
    - If Mode == DIKW: Use `InformationStrategy`. We want the first layer of abstraction to be actionable "Information" derived from "Data" (Chunks).
    - Else: Use `BaseSummaryStrategy`.

2.  **Intermediate Levels (Cluster Summaries from Summaries)**:
    - If Mode == DIKW: Use `KnowledgeStrategy`. We want to synthesize information into "Knowledge" frameworks.
    - Else: Use `BaseSummaryStrategy`.

3.  **Root Level (Final Summary)**:
    - If Mode == DIKW: Use `WisdomStrategy`. The final node must be "Wisdom".
    - Else: Use `BaseSummaryStrategy`.

**Note on Level Detection**: The engine builds the tree bottom-up. We need to track the current recursion depth. However, determining the "Root" in a bottom-up process is tricky because we don't know *a priori* how many levels there will be.
*   **Strategy**: We can apply `InformationStrategy` for the first iteration (Level 1 creation). For subsequent iterations, we apply `KnowledgeStrategy`. After the loop finishes and we have a single root node, we might need a final pass or a specific "Root Refinement" step to transform the top `Knowledge` node into `Wisdom`.
    *   *Alternative*: `RaptorEngine` often creates levels 1..N. Level 1 is from chunks. Level N is the root.
    *   *Refined Logic*:
        - Level 1 generation (from Chunks): Use `InformationStrategy`.
        - Level 2+ generation: Use `KnowledgeStrategy`.
        - **Final Step**: Once the tree is built, take the Root Node (which is Knowledge) and re-process it (or summarize its children) using `WisdomStrategy` to create a new L1 Apex Node.

## 4. Implementation Approach

1.  **Update Config**:
    - Add `ProcessingMode` to `src/domain_models/config.py`.

2.  **Update CLI**:
    - Modify `src/matome/cli.py` to accept `--mode` (default: "default").
    - Pass this mode to the `ProcessingConfig`.

3.  **Refactor Raptor Engine**:
    - In `run()`, check `config.processing_mode`.
    - During the level generation loop:
        - If `level == 0` (processing chunks): Use `InformationStrategy`.
        - If `level > 0`: Use `KnowledgeStrategy`.
    - **Post-Processing**:
        - After the loop, identify the root node.
        - If mode is DIKW, apply `WisdomStrategy` to generate the final L1 node from the top-level L2 nodes (or the single root if it exists).
        - Update `node.metadata.dikw_level` for all generated nodes.

4.  **Verify**:
    - Run the pipeline on test data and inspect the output.

## 5. Test Strategy

### Unit/Integration Testing
- **Config Test**:
    - Verify `ProcessingConfig` defaults to `DEFAULT`.
    - Verify it accepts `dikw`.
- **Engine Logic Test**:
    - Mock `SummarizationAgent`.
    - Run `RaptorEngine` in `DIKW` mode.
    - Verify that:
        - The first round of summarization calls `agent.summarize(strategy=InformationStrategy)`.
        - Subsequent rounds call `agent.summarize(strategy=KnowledgeStrategy)`.
        - The final root node is processed with `WisdomStrategy`.
    - Verify `metadata.dikw_level` is correctly set on the resulting nodes.

### Functional Testing
- **End-to-End**:
    - Run `matome run test.txt --mode dikw`.
    - Check the `summary_dikw.md` (if we implement a specific exporter, or just check the standard markdown).
    - Ideally, the root summary should be very short (Wisdom).
    - The next level should be structural (Knowledge).
