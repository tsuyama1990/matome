# User Test Scenario & Tutorial Plan (Refined)

## 1. Tutorial Strategy

To ensure a seamless onboarding experience and rigorous testing, we will consolidate all user scenarios into a single executable `marimo` notebook. This approach serves dual purposes:
1.  **Interactive Documentation:** Users can modify code cells and see results instantly, learning by doing.
2.  **Automated UAT:** The notebook acts as a system test script that verifies the API contract.

### Mock Mode vs. Real Mode
-   **Mock Mode (Default for CI/Dev):**
    -   Uses pre-generated responses for `SummarizationAgent` to avoid API costs and latency.
    -   Ensures deterministic output for testing logic and UI flow.
    -   Activated by setting `OPENAI_API_KEY="mock"` or passing a flag.
-   **Real Mode:**
    -   Connects to the actual OpenAI API.
    -   Used for quality assurance (Wisdom/Knowledge content check).

## 2. Tutorial Plan

We will create **one master tutorial file**: `tutorials/UAT_AND_TUTORIAL.py`.

### Structure of `UAT_AND_TUTORIAL.py`:

1.  **Introduction & Setup:**
    -   Install dependencies (`uv sync`).
    -   Import `matome` modules.
    -   Setup `DiskChunkStore` (temporary DB).

2.  **Part 1: The "Grok" Moment (Cycle 01)**
    -   Load sample text ("Investment Philosophy").
    -   Run `RaptorEngine` in `dikw` mode.
    -   **Action:** Display the generated "Wisdom" (Root Node).
    -   **Validation:** Assert `metadata.dikw_level == "wisdom"`.

3.  **Part 2: Semantic Zooming (Cycle 03)**
    -   Traverse the tree programmatically.
    -   **Action:** Display children of Root (Knowledge).
    -   **Action:** Display children of Knowledge (Information).
    -   **Validation:** Assert hierarchy depth and node counts.

4.  **Part 3: Interactive Refinement (Cycle 02 & 04)**
    -   **Action:** Select a Knowledge node.
    -   **Action:** Call `interactive_engine.refine_node(node_id, "Explain like I'm 5")`.
    -   **Validation:** Assert the node text changed and `is_user_edited` is True.

5.  **Part 4: Traceability (Cycle 05)**
    -   **Action:** Call `interactive_engine.get_source_chunks(node_id)`.
    -   **Validation:** Assert that a list of `Chunk` objects is returned and they match the original text.

6.  **Part 5: Launching the GUI**
    -   Instructions on how to run `matome serve` to explore the tree visually.

## 3. Tutorial Validation

To validate the tutorial itself:
-   We will run `uv run marimo edit tutorials/UAT_AND_TUTORIAL.py` locally.
-   We will ensure all cells execute without error in "Mock Mode".
-   The final cell will print a success message: **"🎉 All Systems Go: Matome 2.0 is ready for Knowledge Installation."**

## 4. Specific Test Scenarios (Mapping to Cycles)

| ID | Cycle | Scenario Name | Description |
| :--- | :--- | :--- | :--- |
| UAT-01 | C01 | Wisdom Generation | Generate a tree and verify Root is "Wisdom". |
| UAT-02 | C01 | Information Gen | Verify Leaf Summaries are "Actionable". |
| UAT-03 | C02 | Single Refinement | Update a node via Python API and persist to DB. |
| UAT-04 | C02 | Concurrency | Read/Write simultaneously without locking DB. |
| UAT-05 | C03 | Pyramid View | Launch GUI and see the hierarchical layout. |
| UAT-06 | C04 | UI Refinement | Edit a node via the Chat Interface in GUI. |
| UAT-07 | C05 | Source Verification | Click "Show Source" and see original text chunks. |
