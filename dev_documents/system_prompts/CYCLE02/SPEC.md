# Cycle 02: DIKW Generation Engine - Specification

## 1. Summary

Cycle 02 builds upon the `PromptStrategy` infrastructure laid out in Cycle 01 to implement the core differentiation logic of Matome 2.0: the **DIKW Generation Engine**. This cycle focuses on creating specialized prompting strategies for each level of the DIKW hierarchy—Wisdom, Knowledge, and Information (Action)—and integrating them into the `RaptorEngine`.

The key innovation here is **Context-Aware Summarization**. Instead of a generic "summarize this" command, the engine will now dynamically select a strategy based on the current depth of the recursive summarization tree or the specific intent of the node.
-   **Wisdom (L1):** Force the LLM to output a single, profound sentence (20-40 chars).
-   **Knowledge (L2):** Force the LLM to extract structural frameworks and mental models.
-   **Action (L3):** Force the LLM to output actionable checklists.

By the end of this cycle, the CLI will be capable of generating a `chunks.db` where nodes are semantically distinct and tagged with the correct `dikw_level`.

## 2. System Architecture

This cycle focuses on expanding `src/matome/strategies` and modifying the recursion logic in `src/matome/engines`.

### File Structure

```ascii
src/
├── matome/
│   ├── engines/
│   │   └── raptor.py        # [MODIFIED] Logic to select strategy based on level
│   ├── strategies/
│   │   ├── **dikw.py**      # [NEW] Concrete strategies (Wisdom, Knowledge, Action)
│   │   └── base.py          # [MODIFIED] Helper methods for prompt construction
│   └── cli.py               # [MODIFIED] Add --mode dikw flag
```

## 3. Design Architecture

### 3.1. DIKW Strategies (`src/matome/strategies/dikw.py`)

We will implement three distinct classes implementing the `PromptStrategy` protocol.

**`WisdomStrategy`**
-   **Objective:** Extreme abstraction.
-   **System Prompt:** "You are a philosopher. Synthesize the input into a single profound truth."
-   **Constraints:** Max 50 characters. No specific examples.

**`KnowledgeStrategy`**
-   **Objective:** Structural understanding.
-   **System Prompt:** "You are a systems thinker. Extract the underlying mental models and frameworks."
-   **Output Format:** "Concept: [Explanation]" or Bullet points of mechanisms.

**`ActionStrategy`**
-   **Objective:** Utility.
-   **System Prompt:** "You are a pragmatist. Convert the input into a checklist of actionable steps."
-   **Output Format:** "- [ ] Action item"

### 3.2. Engine Logic Update (`src/matome/engines/raptor.py`)

The `RaptorEngine`'s recursive summarization loop (`_process_level`) needs to be aware of the *target level*.

Currently, RAPTOR works bottom-up (Chunks -> Level 1 -> Level 2 -> Root).
In our **Reverse Logic (DIKW)**, we might need to adjust how we view these levels or how we prompt them.
*   **Standard RAPTOR:** Level 0 (Chunks) -> Level 1 (Summaries) -> ... -> Root.
*   **DIKW Mapping:**
    *   Root = Wisdom
    *   High Level = Knowledge
    *   Low Level = Information/Action
    *   Chunks = Data

*Approach:*
1.  **Bottom-Up Generation:** We still build the tree bottom-up (clustering chunks to form actions, clustering actions to form knowledge, clustering knowledge to form wisdom).
2.  **Strategy Selection:**
    -   When summarizing **Chunks (Data)** -> Target is **Information (Action)**.
    -   When summarizing **Information** -> Target is **Knowledge**.
    -   When summarizing **Knowledge** -> Target is **Wisdom** (Root).

*Constraint:* The number of levels in RAPTOR is dynamic based on data size. We may need to force a fixed depth or map dynamic levels to the closest DIKW type.
*Decision:* For this cycle, we will use a **Dynamic Mapping Strategy**:
-   **Root Node:** Always re-summarized with `WisdomStrategy`.
-   **Intermediate Nodes:** Summarized with `KnowledgeStrategy`.
-   **Leaf Summaries (Level 1):** Summarized with `ActionStrategy`.

## 4. Implementation Approach

### Step 1: Implement Strategies (`src/matome/strategies/dikw.py`)
1.  Create `WisdomStrategy`, `KnowledgeStrategy`, `ActionStrategy`.
2.  Refine prompts for each (using the `ALL_SPEC.md` examples).
3.  Implement `parse_output` to enforce constraints (e.g., truncate Wisdom if too long).

### Step 2: Update CLI (`src/matome/cli.py`)
1.  Add a `--mode` argument to the `run` command.
    -   `default`: Uses `LegacyStrategy`.
    -   `dikw`: Uses the new DIKW logic.

### Step 3: Modify RaptorEngine (`src/matome/engines/raptor.py`)
1.  Add `mode` parameter to `__init__`.
2.  In the `_summarize_cluster` method (or equivalent), inject the correct strategy.
    -   If `mode == "dikw"`:
        -   Identify current level (is it L0? is it the final root step?).
        -   Instantiate corresponding strategy.
        -   `agent.summarize(..., strategy=strategy)`.
        -   Set `metadata={"dikw_level": strategy.level}` on the resulting node.

### Step 4: Root Node Refinement
1.  After the RAPTOR tree is built, the root node might just be a generic summary.
2.  Add a post-processing step: `_refine_root_as_wisdom()`.
3.  Re-run the root node text through `WisdomStrategy` to ensure it meets the "20-40 chars" requirement.

## 5. Test Strategy

### Unit Testing
*   **`tests/unit/test_dikw_strategies.py`**:
    *   Test `WisdomStrategy.get_user_prompt`: Ensure it includes "philosophical" instructions.
    *   Test `ActionStrategy.parse_output`: Ensure it formats output as a list (mocking the LLM response).

### Integration Testing
*   **`tests/integration/test_dikw_pipeline.py`**:
    *   Run `matome run sample.txt --mode dikw`.
    *   Load the resulting `chunks.db`.
    *   **Root Check:** Verify root node has `metadata["dikw_level"] == "wisdom"` and text length < 100 chars.
    *   **Leaf Summary Check:** Verify Level 1 nodes have `metadata["dikw_level"] == "information"` (or "action").
    *   **Content Check:** (Qualitative) Manually inspect if actions look like actions.
