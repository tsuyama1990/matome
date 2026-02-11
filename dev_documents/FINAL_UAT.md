# Final User Acceptance Testing (UAT) & Tutorial Plan

## 1. Tutorial Strategy

The goal of the tutorials is not just to test functionality, but to deliver the "Aha! Moment" of Semantic Zooming. We want the user to feel the power of navigating from abstract wisdom down to concrete data.

**Core Concept: "The Knowledge Installation Experience"**
-   **The 'Grok' Moment (Wisdom):** Instant understanding of the core message.
-   **The 'Zoom-In' Thrill (Knowledge):** Exploring the "Why" behind the wisdom.
-   **The 'Action' Payoff (Information):** Walking away with a concrete to-do list.

**Mock Mode Strategy:**
To ensure robust CI/CD and easy onboarding, all tutorials should be runnable in "Mock Mode" where possible.
-   **Real Mode:** Requires `OPENAI_API_KEY`. Uses actual LLM calls.
-   **Mock Mode:** Does not require API keys. Uses pre-generated data or deterministic mocks.
    -   *Implementation:* If `OPENAI_API_KEY` is missing, the system should default to Mock Mode or specific tutorial flags should be used.

## 2. Notebook Plan

We will generate the following Jupyter Notebooks in the `tutorials/` directory.

### `tutorials/01_quickstart.ipynb`: The "Aha! Moment"
**Target Audience:** First-time users.
**Goal:** Demonstrate the full DIKW flow on a sample text without complex setup.

**Content:**
1.  **Setup:** Install dependencies (if needed) and import `matome`.
2.  **Load Data:** Load `test_data/sample.txt` (e.g., the "Seasonal Report" or "Emin's Four Seasons").
3.  **Run (Batch):** execute `matome.run(file, mode="dikw")`.
4.  **Visualize (Static):** Print the Root Node (Wisdom) and its immediate children (Knowledge).
5.  **Interactive Demo (Mini):** Launch a simple inline Panel view (if possible in notebook) or static HTML representation of the tree.

### `tutorials/02_advanced_usage.ipynb`: Deep Dive & Refinement
**Target Audience:** Power users and developers.
**Goal:** Demonstrate the `InteractiveRaptorEngine` API and granular refinement.

**Content:**
1.  **Load Existing DB:** Connect to the `chunks.db` generated in Tutorial 01.
2.  **API Exploration:**
    -   `engine.get_root()`
    -   `engine.get_children(root_id)`
3.  **Refinement (Mock/Real):**
    -   Select a node.
    -   Call `engine.refine_node(id, "Make it shorter")`.
    -   Verify the change.
4.  **Source Verification:**
    -   Call `engine.verify_source(id)`.
    -   Display the raw text chunks.

## 3. Validation Steps (QA Agent Instructions)

When running these notebooks or the full application, the QA Agent should look for the following success criteria:

### 3.1. DIKW Structure Validation
-   **Wisdom (L1):** Is the root node abstract? (e.g., "Invest for the long term.")
-   **Knowledge (L2):** Does the next level explain the mechanism? (e.g., "Compound interest works over time.")
-   **Information (L3):** Are the leaves actionable? (e.g., "- Buy index funds.")
-   **Data (L4):** Do the leaf chunks match the original text?

### 3.2. Interactive Behavior
-   **Refinement:** When a node is refined, does its text change? Does its ID remain constant?
-   **Consistency:** Do the children of a refined node remain accessible?

### 3.3. Technical Stability
-   **Concurrency:** Does the system crash if you try to refine a node while the tree is loading? (It shouldn't).
-   **Persistence:** If you restart the kernel/app, are the refinements saved?

## 4. User Test Scenarios (from Spec)

These are the high-level scenarios driving the UAT.

-   **Scenario A (Semantic Zooming):** Verify the quality and hierarchy of the generated tree.
-   **Scenario B (Interactive Refinement):** Verify the ability to rewrite nodes via chat.
-   **Scenario C (Source Verification):** Verify traceability to original text.
