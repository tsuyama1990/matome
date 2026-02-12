# Final User Acceptance Testing & Tutorial Plan

## 1. Tutorial Strategy

The goal of the tutorials is to guide the user through the "Knowledge Installation" journey, from the initial "Aha!" moment to the mastery of the Semantic Zooming tools. We will convert the user stories defined in `USER_TEST_SCENARIO.md` into executable Jupyter Notebooks.

### 1.1. "Mock Mode" for Reliable Tutorials
To ensure that new users (and CI systems) can run the tutorials without incurring API costs or requiring an OpenAI API key, we will implement a "Mock Mode".
*   **Mechanism:** When the environment variable `OPENAI_API_KEY` is set to `"mock"`, the system will bypass the actual LLM calls.
*   **Data Source:** Instead of calling OpenAI, the `SummarizationAgent` will return pre-generated responses stored in `tests/data/mock_responses/`.
*   **Scenario:** The "Emin's Shikihou" scenario will be the primary mock dataset. The responses for this specific text will be hardcoded/cached so that the tutorial yields deterministic, high-quality results.

### 1.2. "Real Mode" for Exploration
Users with valid API keys can toggle a flag in the notebook to switch to "Real Mode". This allows them to process their own custom text files. The tutorial code must handle this gracefully, checking for the key and warning the user if it's missing.

## 2. Notebook Plan

We will provide three distinct notebooks in the `tutorials/` directory, catering to different levels of engagement.

### 2.1. `tutorials/01_quickstart.ipynb`: The "Aha!" Moment
**Focus:** Immediate gratification. Show, don't just tell.
**Steps:**
1.  **Setup:** Install dependencies and set `OPENAI_API_KEY="mock"`.
2.  **Load Data:** Load the provided sample file (`test_data/emin_shikihou.txt`).
3.  **Run Pipeline:** Execute the `matome` pipeline in DIKW mode.
4.  **Display Wisdom:** Print the generated L1 Wisdom node.
    *   *Expected Reaction:* "Wow, that sums up the book perfectly."
5.  **Launch GUI:** Provide the command (or an embedded IFrame if possible) to open the Matome Canvas.

### 2.2. `tutorials/02_semantic_zooming.ipynb`: Deep Dive
**Focus:** Understanding the DIKW hierarchy and navigation.
**Steps:**
1.  **Inspect Structure:** Programmatically traverse the generated tree.
2.  **Visualize:** Use a simple graph visualization (e.g., `networkx` or `matplotlib`) within the notebook to show the connections between Wisdom, Knowledge, and Information nodes.
3.  **Content Analysis:** Print an L2 Knowledge node and its children L3 Action nodes side-by-side to demonstrate the logical flow ("Why" vs "How").
4.  **Source Trace:** Show how to retrieve the original L4 text chunks for a specific L3 node.

### 2.3. `tutorials/03_interactive_refinement.ipynb`: The Power User
**Focus:** Customizing the knowledge base.
**Steps:**
1.  **Initialize Interactive Session:** Instantiate `InteractiveRaptorEngine` and `InteractiveSession`.
2.  **Select Node:** Programmatically select an L3 node.
3.  **Refine (Chat):** Send a refinement instruction (e.g., "Rewrite this as a bulleted checklist for beginners").
4.  **Verify Update:** Fetch the node again and assert that the text has changed and `metadata.is_user_edited` is `True`.
5.  **Persist:** Show that the changes are saved to `chunks.db`.

## 3. Validation Steps for QA

The QA Agent (or human tester) should follow these steps to validate the final release.

### 3.1. Notebook Execution
*   **Command:** `pytest --nbval tutorials/` (using the `nbval` plugin if available, or manual execution).
*   **Criteria:** All cells must execute without error in "Mock Mode".
*   **Output:** The output cells must contain text that matches the expected DIKW characteristics (e.g., L1 is short, L3 has checkboxes).

### 3.2. GUI Walkthrough
*   **Launch:** Run `uv run matome canvas`.
*   **Browser:** Open `http://localhost:5006`.
*   **Check:**
    1.  Does the page load?
    2.  Is the "Wisdom" card visible?
    3.  Does clicking "Wisdom" reveal "Knowledge"?
    4.  Does the "Refine" button open a chat input?
    5.  Does submitting a refinement update the text on the screen?

### 3.3. Data Integrity
*   **Inspect DB:** Use a SQLite browser to open `results/chunks.db`.
*   **Check:**
    1.  Are there nodes with `dikw_level` set to "wisdom", "knowledge", "information"?
    2.  Are parent-child relationships correctly preserved in the `edges` table (or equivalent structure)?
