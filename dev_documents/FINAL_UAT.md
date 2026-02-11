# Final User Acceptance Testing (UAT) & Tutorial Master Plan

## 1. Tutorial Strategy

The goal of this strategy is to transform the `USER_TEST_SCENARIO.md` into executable, educational, and verifiable tutorials. We will use Jupyter Notebooks (`.ipynb`) as the primary medium for both UAT and user education. This approach allows users to:
1.  **Read:** Understand the concept (DIKW, Semantic Zooming).
2.  **Run:** Execute code blocks to see the system in action.
3.  **Verify:** Check the output against expected results immediately.

### 1.1. "Mock Mode" vs "Real Mode"
To ensure the tutorials are accessible to everyone (including CI/CD environments without API keys) and to prevent unnecessary costs, we will implement a dual-mode execution strategy:

*   **Mock Mode (Default for CI/CD):**
    *   **Logic:** The system will use pre-generated responses or a `MockLLM` wrapper instead of calling OpenAI.
    *   **Data:** It will load a pre-populated `chunks.db` (or a small in-memory sample) that represents the "after" state of a summarization.
    *   **Purpose:** Verifies that the *code* (Python classes, logic) works without crashing. It allows users to explore the *structure* of the data without waiting for generation.

*   **Real Mode (User with API Key):**
    *   **Logic:** The system calls the actual OpenAI API using `SummarizationAgent` with the user's key.
    *   **Data:** It starts from raw text and generates the `chunks.db` from scratch.
    *   **Purpose:** Demonstrates the *quality* of the summarization and the *magic* of the DIKW generation.

### 1.2. Directory Structure
All tutorials will be placed in the `tutorials/` directory at the project root.
-   `tutorials/data/`: Contains sample text files (e.g., `emin_shikiho.txt`).
-   `tutorials/assets/`: Contains images/diagrams for the notebooks.

## 2. Notebook Plan

We will create three key notebooks, progressing from simple usage to advanced customization.

### `tutorials/01_quickstart.ipynb`: The "Aha! Moment" (DIKW Visualization)
**Goal:** Demonstrate the "Wisdom to Data" hierarchy immediately.
**Prerequisites:** None (runs in Mock Mode by default).
**Content:**
1.  **Introduction:** Briefly explain Matome 2.0 and the DIKW concept.
2.  **Load Data:** Load a pre-processed `chunks.db` (containing the "Emin Yurumazu" sample).
3.  **Visualize Wisdom (L1):** Display the root node's "Wisdom" text.
    *   *Action:* User reads the 30-character insight.
4.  **Semantic Zoom (L1 -> L2):** Run a cell to "zoom in" and show the children (Knowledge) of that Wisdom.
    *   *Action:* User sees the supporting frameworks.
5.  **Interactive Query:** A simple cell where the user can "ask" the system about a specific node (simulating the chat interface).

### `tutorials/02_advanced_usage.ipynb`: The "Builder" Experience (Real Mode)
**Goal:** Show how to generate a DIKW tree from scratch.
**Prerequisites:** `OPENAI_API_KEY`.
**Content:**
1.  **Setup:** Configure the `InteractiveRaptorEngine` and `SummarizationAgent` with `WisdomStrategy`.
2.  **Process:** Run the pipeline on a raw text file (`tutorials/data/sample.txt`).
    *   *Observation:* Watch the progress bars as it chunks, embeds, clusters, and summarizes.
3.  **Inspect Metadata:** Write code to query the `chunks.db` and verify that nodes have `dikw_level="wisdom"`, `dikw_level="knowledge"`, etc.
4.  **Custom Refinement:** Programmatically call `engine.refine_node(node_id, instruction="Make it funnier")` and verify the change in the DB.

### `tutorials/03_interactive_app.ipynb`: The Full GUI Experience
**Goal:** Launch the Panel application directly from the notebook.
**Prerequisites:** `panel` library.
**Content:**
1.  **Launch:** Run `matome.gui.app.serve()` (or equivalent) to render the Panel app within the notebook output cell.
2.  **Walkthrough:** Guided steps to:
    *   Click the Root Node.
    *   Drill down to Level 3.
    *   Use the Chat Input to refine a node.
    *   (Optional) Check the "Source" tab to see original text.

## 3. Validation Steps

The Quality Assurance (QA) Agent or human tester should perform the following checks when running these notebooks:

### Validation Checklist
1.  **Dependencies:** Ensure `uv sync` or `pip install .[dev]` installs all required packages (`panel`, `watchfiles`, `jupyter`).
2.  **Mock Mode Success:**
    *   Run `01_quickstart.ipynb` *without* an API key.
    *   **Pass Criteria:** All cells execute without error. The "Wisdom" text is displayed.
3.  **Real Mode Success:**
    *   Set `OPENAI_API_KEY`. Run `02_advanced_usage.ipynb`.
    *   **Pass Criteria:** The process completes. A new `chunks.db` is created. `refine_node` updates the text in the DB.
4.  **GUI Rendering:**
    *   Run `03_interactive_app.ipynb`.
    *   **Pass Criteria:** The Panel widget appears in the output area. Buttons are clickable.
5.  **Linting:** The notebooks themselves should be clean (no huge error tracebacks saved in the file).

### Automated Testing
We will also include a `tests/tutorials/test_notebooks.py` (using `nbval` or similar if possible, otherwise a simple execution script) to automatically run these notebooks in the CI pipeline (in Mock Mode) to prevent regression.
