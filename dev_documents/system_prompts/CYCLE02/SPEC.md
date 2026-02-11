# Cycle 02: DIKW Engine Logic

## 1. Summary

In this cycle, we implement the core logic for "Semantic Zooming" by creating specific `PromptStrategy` implementations for each layer of the DIKW hierarchy: **Wisdom**, **Knowledge**, and **Information (Action)**. We will also update the `RaptorEngine` to intelligently select the appropriate strategy based on the current tree depth during the summarization process.

This transforms the engine from a generic summarizer into a structured knowledge extractor.

## 2. System Architecture

We will expand `src/matome/agents/strategies.py` and modify `src/matome/engines/raptor.py`.

```ascii
src/matome/
├── agents/
│   └── **strategies.py**       # [MOD] Add Wisdom, Knowledge, Action strategies
├── engines/
│   └── **raptor.py**           # [MOD] Add logic to map Tree Level -> Strategy
└── domain_models/
    └── **config.py**           # [MOD] Add ProcessingMode Enum
```

### Files to Modify/Create

1.  **`src/domain_models/config.py`**
    *   **Action**: Add `ProcessingMode` Enum (`DEFAULT`, `DIKW`). Add field to `ProcessingConfig`.
2.  **`src/matome/agents/strategies.py`**
    *   **Action**: Implement `WisdomStrategy`, `KnowledgeStrategy`, `ActionStrategy`.
3.  **`src/matome/engines/raptor.py`**
    *   **Action**: Update `RaptorEngine.run` loop to instantiate `SummarizationAgent` with the correct strategy for the current level.

## 3. Design Architecture

### 3.1. Strategies Implementation

Each strategy will implement `PromptStrategy` but with distinct prompt templates.

*   **`WisdomStrategy` (Level 0 / Root)**
    *   **Prompt Goal**: "Distill this into a single profound truth or aphorism (20-50 chars)."
    *   **Constraint**: Extremely short, abstract, "Why".
*   **`KnowledgeStrategy` (Level 1)**
    *   **Prompt Goal**: "Explain the mental models and mechanisms behind this."
    *   **Constraint**: Structural explanation, "How it works".
*   **`ActionStrategy` (Level 2+)**
    *   **Prompt Goal**: "Extract actionable steps and checklists."
    *   **Constraint**: Concrete, "What to do".

### 3.2. RaptorEngine Logic Update

The engine needs to know which level it is processing.

*   **Current Logic**:
    ```python
    summarizer.summarize(text) # Always same strategy
    ```
*   **New Logic**:
    ```python
    if config.mode == ProcessingMode.DIKW:
        if level == 0:
            strategy = WisdomStrategy()
        elif level == 1:
            strategy = KnowledgeStrategy()
        else:
            strategy = ActionStrategy()
    else:
        strategy = BaseSummaryStrategy()

    summarizer.summarize(text, strategy=strategy)
    ```

## 4. Implementation Approach

1.  **Config Update**: Add `ProcessingMode` to `domain_models/config.py`.
2.  **Strategy Implementation**: Write the 3 new classes in `strategies.py`. Focus on prompt engineering for each.
3.  **Engine Update**: Modify `RaptorEngine` to select the strategy based on the current iteration/level.
    *   *Note*: RAPTOR builds bottom-up. Level 0 is usually leaves. We need to be careful with level indexing. If RAPTOR is bottom-up, the *last* level (root) is Wisdom.
    *   *Correction*: The spec says "L1: Wisdom (Root)". RAPTOR processes from leaves (Data) -> ... -> Root.
    *   *Logic*:
        *   Leaves = Data (No summarization, just chunks).
        *   Level 1 (First clustering) -> ActionStrategy (Information).
        *   Level 2 -> KnowledgeStrategy (Knowledge).
        *   Final Root -> WisdomStrategy (Wisdom).
    *   *Dynamic Depth*: If tree is deeper, intermediate levels might repeat `KnowledgeStrategy`. The final reduction to single node must use `WisdomStrategy`.

## 5. Test Strategy

### 5.1. Unit Testing
*   **Strategies**: Test `WisdomStrategy.format_prompt` ensures the prompt contains "aphorism" and "20-50 characters".
*   **Engine Logic**: Mock the `SummarizationAgent` and verify that `RaptorEngine` calls it with the correct strategy at different levels (e.g., first iteration uses Action, last uses Wisdom).

### 5.2. Integration Testing
*   **Full Run**: Execute `matome run --mode dikw`.
*   **Verification**: Inspect the generated `chunks.db` or output markdown.
    *   Root node text should be short (Wisdom).
    *   Child nodes should be actionable (Information).
