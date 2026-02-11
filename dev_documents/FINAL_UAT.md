# Final User Acceptance Testing (UAT) & Tutorial Plan

## 1. Tutorial Strategy

The goal of the tutorials is to guide the user from a static understanding of text summarization to the dynamic "Knowledge Installation" experience provided by Matome 2.0. The strategy revolves around two key modes:

### 1.1. Mock Mode (CI/CD & Quick Start)
To ensure accessibility and robust testing without requiring API keys, we will implement a "Mock Mode".
- **Concept:** The `SummarizationAgent` will have a flag (`api_key="mock"`) that returns pre-defined, deterministic summaries instead of calling the LLM.
- **Benefit:** Users can run the notebooks immediately after cloning the repo to understand the *flow* and *data structures* without incurring costs or configuration overhead.
- **Data:** We will use the included `test_data/エミン流「会社四季報」最強の読み方.txt` (or a smaller excerpt) as the standard input.

### 1.2. Real Mode (The "Aha!" Moment)
The true value of Matome 2.0 is in the quality of the "Wisdom" and "Knowledge" it extracts.
- **Concept:** Users provide their valid `OPENAI_API_KEY` (or OpenRouter key) in a `.env` file.
- **Experience:** The tutorials will check for this key. If present, they run the actual RAPTOR process. The output will be a rich, hierarchical tree that the user can explore.
- **Verification:** The user should experience the "Semantic Zooming" effect—starting with a single profound sentence (Wisdom) and drilling down into actionable advice (Information).

## 2. Notebook Plan

We will create three Jupyter Notebooks in the `tutorials/` directory, corresponding to the user journey stages.

### `tutorials/01_quickstart.ipynb`: The DIKW Tree Generation
**Goal:** Demonstrate the core batch engine generating a Wisdom-Knowledge-Information tree.
**Steps:**
1.  **Setup:** Install dependencies (`uv sync` or `pip install .`).
2.  **Ingestion:** Load the sample text (`test_data/source.txt`).
3.  **Execution:** Initialize `RaptorEngine` with `WisdomStrategy`, `KnowledgeStrategy`, and `ActionStrategy`.
4.  **Run:** Execute `engine.run(text)`.
5.  **Inspect:** Print the generated `DocumentTree`.
    - Show the Root Node (Wisdom).
    - Show Level 1 Nodes (Knowledge).
    - Show Leaf Nodes (Data).
**Success Metric:** The user sees a clear hierarchy where the root is abstract and leaves are concrete.

### `tutorials/02_interactive_refinement.ipynb`: The Backend Logic
**Goal:** Demonstrate how the "Interactive Engine" works programmatically (before adding the GUI layer).
**Steps:**
1.  **Load:** Open the `chunks.db` created in Tutorial 01 using `DiskChunkStore`.
2.  **Initialize:** Create an `InteractiveRaptorEngine` instance.
3.  **Refine:** Select a specific node ID (e.g., a "Knowledge" node).
    - Call `engine.refine_node(node_id, instruction="Make this more simple")`.
4.  **Verify:** Fetch the node again from the store and print the `text` and `metadata`.
    - Assert that `is_user_edited` is `True`.
    - Assert that the text has changed (in Real Mode) or is the mock response (in Mock Mode).
**Success Metric:** The user understands that the tree is mutable and can be updated node-by-node.

### `tutorials/03_gui_walkthrough.ipynb`: The Matome Canvas
**Goal:** Explain how to launch and use the Panel-based GUI.
**Steps:**
1.  **Explanation:** Describe the MVVM architecture (Model-View-ViewModel).
2.  **Code Walkthrough:** Show the snippet for `InteractiveSession` and `MatomeCanvas`.
3.  **Launch Command:** Provide the command `panel serve src/matome/ui/app.py --autoreload`.
4.  **Screenshots:** Since Notebooks cannot easily embed a full interactive Panel server in all environments, include screenshots of:
    - The initial "Wisdom Card".
    - The "Drill-Down" view with children nodes.
    - The "Refinement Chat" interface.
**Success Metric:** The user successfully launches the app in their terminal and replicates the screenshots.

## 3. Validation Steps

The Quality Assurance (QA) agent or the user should verify the following points when running the tutorials:

### 3.1. Output Quality (Real Mode)
*   **Wisdom Node:** Must be short (20-50 chars), philosophical, and abstract. (e.g., "Market distortions reveal themselves only to the patient observer.")
*   **Action Node:** Must contain bullet points or checklists. (e.g., "- [ ] Check PSR < 1.0", "- [ ] Monitor monthly reports")
*   **Hallucination Check:** Randomly select a leaf node and verify it matches the source text chunk.

### 3.2. System Behavior
*   **Mock Mode Fallback:** If no API key is present, the system MUST NOT crash. It should log a warning and return mock data.
*   **Database Locking:** During Tutorial 02 (Refinement), ensure that reading the tree (e.g., `store.get_node(root_id)`) works even immediately after a write operation.
*   **State Persistence:** Close the notebook/kernel, reopen it, load the `DiskChunkStore`. The "Refined" node from Tutorial 02 should still be there with its new text.

### 3.3. Architecture Compliance
*   **Strict Typing:** Run `mypy src` and ensure no errors.
*   **Linting:** Run `ruff check .` and ensure clean output.
*   **Test Coverage:** Run `pytest --cov=src` and ensure core logic (`RaptorEngine`, `InteractiveRaptorEngine`, `DiskChunkStore`) has >80% coverage.
