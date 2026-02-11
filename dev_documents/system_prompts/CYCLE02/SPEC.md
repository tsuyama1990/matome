# Cycle 02: DIKW Generation Engine - Specification

## 1. Summary

In this cycle, we will implement the core logic for "Semantic Zooming" by creating the specific `PromptStrategy` implementations for the DIKW (Data, Information, Knowledge, Wisdom) hierarchy. We will also update the `RaptorEngine` to utilize these strategies appropriately based on the tree level.

The goal is to enable the system to generate distinct types of summaries at different levels of abstraction:
*   **Level 0 (Leaves) -> ActionStrategy**: Generate actionable information (how-to, checklists) from raw data.
*   **Level 1 (Branches) -> KnowledgeStrategy**: Synthesize actions into structural knowledge (why, frameworks).
*   **Level 2+ (Root) -> WisdomStrategy**: Distill knowledge into core wisdom (philosophy, aphorisms).

This logic replaces the generic "Chain of Density" summarization when the `--mode dikw` flag is used.

## 2. System Architecture

```text
src/
├── matome/
│   ├── agents/
│   │   ├── **strategies.py**       # UPDATED: Add WisdomStrategy, KnowledgeStrategy, ActionStrategy
│   │   └── summarizer.py           # (No change, uses injected strategy)
│   ├── engines/
│   │   └── **raptor.py**           # UPDATED: Add logic to select strategy based on tree level
├── domain_models/
│   └── config.py                   # UPDATED: Add ProcessingMode enum ("default", "dikw")
tests/
├── **test_dikw_strategies.py**     # CREATED: Unit tests for new strategies
└── test_raptor_dikw.py             # CREATED: Integration test for DIKW mode
```

### Key Components

*   **`src/matome/agents/strategies.py`**: Will house the three new concrete implementations of `PromptStrategy`.
*   **`src/matome/engines/raptor.py`**: The `RaptorEngine.run` method (or a helper method) will be updated to check `config.processing_mode`. If `DIKW`, it will inject the appropriate strategy into the `SummarizationAgent` for each level of recursion.
*   **`src/domain_models/config.py`**: Add `ProcessingMode(StrEnum)` with values `DEFAULT` and `DIKW`.

## 3. Design Architecture

### 3.1. DIKW Strategies

We will implement three classes inheriting from `PromptStrategy` (or `BaseSummaryStrategy` if code reuse is beneficial).

#### `ActionStrategy (Information)`
*   **Prompt Goal**: Extract "What to do".
*   **Output Format**: Markdown checklist (`- [ ] ...`) or bullet points.
*   **Constraint**: Must be concrete and actionable.
*   **Example**: "To improve code quality, run `ruff check` before committing."

#### `KnowledgeStrategy`
*   **Prompt Goal**: Extract "How it works" and "Why it matters".
*   **Output Format**: Structured text with headings (e.g., `### Mechanism`, `### Rationale`).
*   **Constraint**: Explain relationships between concepts.
*   **Example**: "Linting ensures code consistency by enforcing a unified style guide, which reduces cognitive load during reviews."

#### `WisdomStrategy`
*   **Prompt Goal**: Extract "The Core Truth".
*   **Output Format**: A single paragraph or a short list of aphorisms.
*   **Constraint**: Maximum abstraction, minimal detail. < 50 words ideally.
*   **Example**: "Consistency is the foundation of maintainability."

### 3.2. Raptor Engine Logic

The `RaptorEngine` needs to be aware of the tree depth.

```python
# Pseudo-code in raptor.py

def _process_level(self, chunks: List[Chunk], level: int) -> List[SummaryNode]:
    # Determine strategy
    if self.config.processing_mode == ProcessingMode.DIKW:
        if level == 0:
            strategy = ActionStrategy()
        elif level == 1:
            strategy = KnowledgeStrategy()
        else:
            strategy = WisdomStrategy()
    else:
        strategy = BaseSummaryStrategy()

    # Pass strategy to summarizer (either by re-initializing or setting property)
    # Ideally, Summarizer.summarize() accepts an override strategy.
    summary = self.summarizer.summarize(text_list, strategy=strategy)
    ...
```

**Note**: The `Summarizer` protocol/class must support `summarize(..., strategy=...)` as defined in Cycle 01.

## 4. Implementation Approach

### Step 1: Implement Strategies
1.  In `src/matome/agents/strategies.py`, implement `ActionStrategy`, `KnowledgeStrategy`, and `WisdomStrategy`.
2.  Tune the prompts for each to match the "Success Criteria" in `ALL_SPEC.md`.

### Step 2: Update Configuration
1.  In `src/domain_models/config.py`, add `ProcessingMode` enum.
2.  Update `ProcessingConfig` to include `processing_mode: ProcessingMode = ProcessingMode.DEFAULT`.

### Step 3: Update Raptor Engine
1.  Modify `src/matome/engines/raptor.py`.
2.  Inside the recursion loop (or level processing loop), add the logic to select the strategy based on `level` and `config.processing_mode`.
3.  Ensure that when a `SummaryNode` is created, its `metadata.dikw_level` is set correctly (e.g., `DIKWLevel.INFORMATION` for level 0 output).

### Step 4: CLI Integration
1.  Update `src/matome/cli.py` (if necessary) to expose the `--mode` argument (it might be handled automatically by Pydantic/Typer if using `ProcessingConfig`).

## 5. Test Strategy

### 5.1. Strategy Unit Tests

**`tests/test_dikw_strategies.py`**
*   **Test ActionStrategy**:
    *   Input: A paragraph describing a process.
    *   Assert: Output contains "- [ ]" or similar checklist markers.
*   **Test WisdomStrategy**:
    *   Input: A long detailed text.
    *   Assert: Output is short (< 50 words or specific char limit) and abstract.

### 5.2. Engine Integration Tests

**`tests/test_raptor_dikw.py`**
*   **Test DIKW Tree Generation**:
    *   Mock the LLM to return specific strings based on the strategy prompt (e.g., if prompt contains "Action", return "- [ ] Do this").
    *   Run `RaptorEngine` with `mode="dikw"`.
    *   Inspect the resulting `SummaryNode` objects in `DiskChunkStore`.
    *   Assert that leaf nodes (Level 0) have `dikw_level="information"`.
    *   Assert that root node (Level N) has `dikw_level="wisdom"`.
