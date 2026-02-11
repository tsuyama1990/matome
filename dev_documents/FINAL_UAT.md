# Final UAT & Tutorial Master Plan

## 1. Tutorial Strategy

The goal of the User Acceptance Testing (UAT) and tutorials is to demonstrate the unique value proposition of Matome 2.0: **"Knowledge Installation" via Semantic Zooming**.

### 1.1. The "Aha! Moment"
We will use the provided test data (`test_data/エミン流「会社四季報」最強の読み方.txt`) to showcase how a long, complex text is distilled into a single, profound "Wisdom" (L1), which can then be unpacked into "Actionable Knowledge" (L3).

### 1.2. Mock Mode vs. Real Mode
To ensure reproducibility and accessibility (especially for users without API keys), tutorials will support two modes:
*   **Real Mode**: Uses `OPENROUTER_API_KEY` to call actual LLMs.
*   **Mock Mode**: Triggered when `OPENROUTER_API_KEY="mock"`. In this mode, the `SummarizationAgent` loads pre-generated responses from `tests/data/mock_responses/`. This allows the CI/CD pipeline and new users to run the full UI flow without costs or latency.

## 2. Notebook Plan

We will generate the following Jupyter Notebooks in the `tutorials/` directory.

### `tutorials/01_quickstart.ipynb`: The "Aha! Moment"
*   **Objective**: Demonstrate the "Zero to Wisdom" flow.
*   **Steps**:
    1.  Initialize `ProcessingConfig` (Mock Mode by default).
    2.  Run `RaptorEngine` on the sample text.
    3.  Display the generated Root Node (Wisdom).
    4.  **The "Aha!"**: Show how 2000 characters were compressed into a 30-character insight.

### `tutorials/02_semantic_zooming.ipynb`: Exploring the Tree
*   **Objective**: Visualize the DIKW hierarchy.
*   **Steps**:
    1.  Load the `chunks.db` generated in the previous step.
    2.  Use a simple textual visualization (ascii tree) to show the relationship:
        `Wisdom -> Knowledge -> Information -> Data`.
    3.  Demonstrate how to access metadata (`dikw_level`) programmatically.

### `tutorials/03_interactive_refinement.ipynb`: Customizing Knowledge
*   **Objective**: Simulate the GUI interaction via code (Backend API).
*   **Steps**:
    1.  Initialize `InteractiveRaptorEngine`.
    2.  Select a specific L3 (Action) node.
    3.  Send a refinement prompt: "Rewrite this for a 10-year-old".
    4.  Verify that the node text has changed and `refinement_history` is updated.

## 3. Validation Steps

The QA Agent (or human tester) should verify the following criteria when running the notebooks:

### 3.1. Structure Verification
*   **Check**: Does the root node have `dikw_level="wisdom"`?
*   **Check**: Do leaf nodes have `dikw_level="data"`?
*   **Check**: Are there at least 3 layers of depth?

### 3.2. Content Verification
*   **Check**: Is the Wisdom node (L1) short (approx. 20-50 chars)?
*   **Check**: Does the Information node (L3) contain actionable items (checklists/bullet points)?

### 3.3. Interaction Verification
*   **Check**: After running the refinement step in Tutorial 03, is the `is_user_edited` flag set to `True`?
*   **Check**: Does the `refinement_history` list contain the user's prompt?

### 3.4. System Stability
*   **Check**: Do the notebooks run to completion without `sqlite3.OperationalError` (database locked)?
*   **Check**: Does "Mock Mode" work without requiring an actual network connection?
