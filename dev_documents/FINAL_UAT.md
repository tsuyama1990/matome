# Final User Acceptance Testing (UAT) & Tutorial Plan

## 1. Tutorial Strategy

The goal of the UAT phase is not just to verify functionality, but to deliver an "Aha! Moment" to the user. We will achieve this by providing executable Jupyter Notebooks that demonstrate the core value proposition: **Semantic Zooming** and **Interactive Refinement**.

### Strategy: "Mock Mode" vs "Real Mode"
To ensure these tutorials are verifiable in a CI/CD environment (where API costs and latency are concerns), we will implement a "Mock Mode".
- **Real Mode (Default):** Uses the user's `OPENAI_API_KEY` to generate live summaries.
- **Mock Mode (CI/Tutorials):** Uses a predefined set of responses (stored in `tests/data/mock_responses/`) when the API key is set to `"mock"`. This guarantees deterministic output for the tutorials.

## 2. Notebook Plan

We will generate two primary notebooks in the `tutorials/` directory.

### Tutorial 01: The "Aha! Moment" (Quickstart)
**File:** `tutorials/01_quickstart.ipynb`
**Goal:** Demonstrate the instant extraction of "Wisdom" from a complex text.
**Scenario:**
1.  **Setup:** Install dependencies and set API key (or use mock).
2.  **Load Data:** Load `test_data/emin_shikiho.txt` (or similar sample).
3.  **Run Engine:** Execute `matome run` with `--mode dikw`.
4.  **Visualize:** Display the root "Wisdom" node.
5.  **Zoom:** Programmatically retrieve and display the child "Knowledge" nodes.
**Expected Outcome:** The user sees a 30-character profound insight derived from 2000 characters of text.

### Tutorial 02: Interactive Refinement (Deep Dive)
**File:** `tutorials/02_interactive_refinement.ipynb`
**Goal:** Demonstrate the ability to "talk to your knowledge base."
**Scenario:**
1.  **Load Session:** Open the `DiskChunkStore` from Tutorial 01.
2.  **Select Node:** Pick a specific "Knowledge" node (e.g., about PSR).
3.  **Refine:** Use `InteractiveRaptorEngine.refine_node()` with the instruction: "Explain this to a 12-year-old."
4.  **Verify:** Show the old text vs. the new text side-by-side.
5.  **Trace:** Show the original source chunks for that node.
**Expected Outcome:** The node's content is rewritten in simple language without regenerating the entire tree.

## 3. Validation Steps

The Quality Assurance (QA) agent or user should perform the following checks:

### Automated Validation (CI)
1.  **Execution:** Run `pytest --nbval tutorials/` (using `nbval` plugin or similar script).
2.  **Mock Check:** Ensure `OPENAI_API_KEY=mock` is set during CI.
3.  **Output Check:** Verify that cell outputs contain specific expected strings (e.g., "Wisdom:", "Refined Node:").

### Manual Validation (User)
1.  **Visual Inspection:** Open `tutorials/01_quickstart.ipynb`.
2.  **Run All:** Click "Run All Cells".
3.  **Latent Check:** Confirm that the first summary appears within reasonable time (or instantly in mock mode).
4.  **Content Quality:** Read the "Wisdom" output. Does it feel profound?
5.  **Interaction:** In Tutorial 02, change the refinement instruction (e.g., "Make it sarcastic") and verify the AI adapts.
