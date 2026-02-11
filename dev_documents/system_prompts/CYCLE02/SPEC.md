# Cycle 02: DIKW Generation Engine - Specification

## 1. Summary

Building on the `PromptStrategy` pattern established in Cycle 01, this cycle implements the core logic for "Semantic Zooming." We will create specific strategies corresponding to the DIKW hierarchy: `WisdomStrategy` (Level 1), `KnowledgeStrategy` (Level 2), and `ActionStrategy` (Level 3). The `RaptorEngine` will be updated to dynamically select the appropriate strategy based on the current tree depth, ensuring that summaries at different levels serve distinct purposes rather than just being shorter versions of the text.

## 2. System Architecture

We expand `src/matome/agents/strategies.py` with concrete implementations and modify `src/matome/engines/raptor.py` to use them.

```ascii
src/
├── matome/
│   ├── agents/
│   │   ├── **strategies.py**  # MODIFY: Add Wisdom, Knowledge, Action strategies
│   │   └── summarization.py   # MODIFY: Ensure context (level) is passed
│   └── engines/
│       └── **raptor.py**      # MODIFY: Logic to map Tree Level -> Strategy
```

**Key Changes:**
1.  **`src/matome/agents/strategies.py`**:
    -   `WisdomStrategy`: Generates high-level axioms.
    -   `KnowledgeStrategy`: Extracts structural logic/frameworks.
    -   `ActionStrategy`: Extracts actionable checklists.
    -   `DIKWHierarchyStrategy`: A composite strategy or factory that selects one of the above based on context.
2.  **`src/matome/engines/raptor.py`**:
    -   Update the recursive summarization loop. When calling `summarizer.summarize`, pass the current tree `level` in the context.

## 3. Design Architecture

### 3.1. DIKW Strategies

Each strategy implements `PromptStrategy` but with distinct prompt templates.

**`WisdomStrategy` (L1)**
-   **Goal:** Abstract, context-free truth.
-   **Prompt Key:** "Extract the core philosophical message or 'Wisdom' from this text. It should be a single, profound statement (20-50 chars). Do not use specific names or numbers."

**`KnowledgeStrategy` (L2)**
-   **Goal:** Logical structure / Mental Model.
-   **Prompt Key:** "Identify the 'Knowledge' or framework that supports the core message. Explain 'Why' this is true. Use analogies or logical steps."

**`ActionStrategy` (L3)**
-   **Goal:** Concrete instructions.
-   **Prompt Key:** "Extract 'Information' as a checklist of actionable steps. What should the reader DO tomorrow? Use bullet points."

### 3.2. Mapping Logic (The "DIKW Engine")

The `RaptorEngine` typically processes from leaves (L0) up to the root.
-   **Leaves (L0):** Data (Original Chunks).
-   **Level 1 (Clusters of Chunks):** Should produce **Action** (L3) or **Information**.
-   **Level 2 (Clusters of L1):** Should produce **Knowledge** (L2).
-   **Level 3+ (Root):** Should produce **Wisdom** (L1).

*Note: The RAPTOR levels (0, 1, 2...) are bottom-up. The DIKW levels (Wisdom, Knowledge...) are top-down. The mapping needs to be carefully defined in `constants.py` or the Engine configuration.*

**Proposed Mapping:**
-   `tree_level == 1` -> Use `ActionStrategy`
-   `tree_level == 2` -> Use `KnowledgeStrategy`
-   `tree_level >= 3` (Root) -> Use `WisdomStrategy`

## 4. Implementation Approach

### Step 1: Implement Strategies
1.  In `src/matome/agents/strategies.py`, create the classes `WisdomStrategy`, `KnowledgeStrategy`, `ActionStrategy`.
2.  Add the specific prompt templates to each class (referencing `constants.py` for the actual text).

### Step 2: Update Summarization Interface
1.  Ensure `SummarizationAgent.summarize` accepts `level` or `context` as an argument.
2.  If it doesn't, update the signature: `def summarize(self, text, strategy: PromptStrategy = None, context: dict = None)`.

### Step 3: Integrate with RaptorEngine
1.  In `RaptorEngine._process_level` (or equivalent loop), determine the strategy to use based on the current `level`.
2.  Instantiate the appropriate strategy (e.g., `strategy = strategies.get_strategy_for_level(level)`).
3.  Pass this strategy to the `summarizer`.

## 5. Test Strategy

### 5.1. Unit Testing (Prompts)
-   **Verification:** Create a test that instantiates each strategy and checks the generated prompt.
-   **Wisdom:** Prompt must contain "philosophical", "abstract", "20-50 chars".
-   **Action:** Prompt must contain "checklist", "actionable", "bullet points".

### 5.2. Integration Testing (Generation)
-   **Mock LLM:** Use a mock LLM that returns distinct strings based on the prompt.
    -   If prompt contains "philosophical", return "The universe is vast."
    -   If prompt contains "checklist", return "- Do laundry."
-   **Run Engine:** Run `RaptorEngine` with this mock.
-   **Inspect DB:** Check `SummaryNode` objects.
    -   Nodes at Level 3 (Root) should have text "The universe is vast."
    -   Nodes at Level 1 should have text "- Do laundry."

### 5.3. Manual Quality Check
-   **Run on Sample:** Run the real CLI with a sample text (e.g., the "Seasonal Report" example).
-   **Read Output:** Open `summary.md` (if it dumps all nodes) or `chunks.db` and manually verify that the root node is indeed "Wisdom" and lower nodes are "Actions".
