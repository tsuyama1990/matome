# Final User Acceptance Test (UAT) & Tutorial Master Plan

## 1. Tutorial Strategy

The tutorial strategy for Matome 2.0 is designed to facilitate "Knowledge Installation." We are not just teaching a tool; we are teaching a new way of consuming information. The tutorials will be delivered as executable Jupyter Notebooks that serve a dual purpose: they educate the user and act as verifiable test cases for the system.

### 1.1. The "Aha! Moment" First
The very first interaction must deliver the "Wisdom" (Level 1) immediately. We will not burden the user with configuration or long processing times in the first step.
-   **Strategy**: Use pre-computed data for the initial tutorial. The user opens the notebook, runs a cell, and immediately sees the "Semantic Zooming" interface populated with a fascinating example (e.g., "The Psychology of Money" or the provided "Emin's Quarterly Report Strategy").
-   **Goal**: Demonstrate value within 30 seconds.

### 1.2. Mock Mode vs. Real Mode
To ensure these tutorials are robust and testable in CI/CD environments (GitHub Actions) where API keys might be restricted, the system will support a "Mock Mode."
-   **Mock Mode**: The `SummarizationAgent` and `PromptStrategy` will return pre-defined strings instead of calling the OpenAI API. The `InteractiveRaptorEngine` will simulate processing delays.
-   **Real Mode**: Connects to the actual API for live generation.
-   **Implementation**: Tutorials will check for `OPENAI_API_KEY`. If missing, they will default to Mock Mode with a clear banner explaining the limitation.

## 2. Notebook Plan

We will generate the following Jupyter Notebooks in the `tutorials/` directory.

### `tutorials/01_quickstart_wisdom.ipynb`
**Title**: "Instant Wisdom: The Power of Semantic Zooming"
**Objective**: The "Aha! Moment." Experience the DIKW hierarchy without setup.
**Content**:
1.  **Introduction**: Brief explanation of Wisdom vs. Information.
2.  **Load Pre-computed Tree**: Load a bundled `chunks.db` containing the "Emin's Quarterly Report" dataset.
3.  **Visualizing Wisdom**: Display the root node using the Panel viewer.
4.  **The Zoom**: Instruct the user to click the root node. Reveal the "Knowledge" branches.
5.  **The Action**: Click a branch to see the "Action" checklist.
6.  **Conclusion**: "You just digested a 2000-character article in 3 clicks."

### `tutorials/02_interactive_refinement.ipynb`
**Title**: "Make It Yours: Interactive Knowledge Refinement"
**Objective**: Learn how to customize the knowledge base using the Chat interface.
**Content**:
1.  **Setup**: Initialize a fresh `InteractiveSession`.
2.  **Scenario**: "The AI's explanation of 'PSR' is too technical."
3.  **Action**: Use the API to send a refinement instruction: "Explain this to a middle schooler."
4.  **Verification**: Observe the node update in real-time.
5.  **Persistence Check**: Restart the session and verify the simplified explanation remains.

### `tutorials/03_end_to_end_generation.ipynb`
**Title**: "From Scratch: Installing New Knowledge"
**Objective**: Run the full pipeline on a new text file.
**Content**:
1.  **Ingestion**: Point the system to a raw text file (e.g., a sample README or article).
2.  **Process**: Run `matome run --mode dikw`. Visual progress bar.
3.  **Result**: Open the generated database in the Canvas.
4.  **Validation**: Verify that all 4 levels (Wisdom, Knowledge, Information, Data) were generated.

## 3. Validation Steps for QA Agent

The Quality Assurance (QA) Agent should perform the following checks when validating the tutorials and the system.

### 3.1. General System Checks
-   [ ] **Dependency Check**: Ensure `panel`, `watchfiles`, and `openai` (or compatible) are installed.
-   [ ] **Environment**: Ensure `.env` is loaded if present, but the system doesn't crash if it's missing (falls back to Mock/Error gracefully).

### 3.2. Tutorial Validation
-   [ ] **01_quickstart_wisdom.ipynb**:
    -   Must run without exceptions even without an API key.
    -   Must render a Panel object (check for `pn.Column` or `pn.Row` in output).
    -   The `chunks.db` file must exist in the expected `test_data` or `assets` location.
-   [ ] **02_interactive_refinement.ipynb**:
    -   In Mock Mode, the "Refined" text should be a predictable placeholder (e.g., "[MOCK] Refined text based on: ...").
    -   The `is_user_edited` flag in the node metadata must flip to `True` after refinement.
-   [ ] **03_end_to_end_generation.ipynb**:
    -   This test requires an API key or a robust Mocking strategy that simulates the entire RAPTOR pipeline.
    -   Check that the output `chunks.db` size > 0.
    -   Query the DB to ensure at least one Root Node exists with `metadata.dikw_level == 'wisdom'`.

### 3.3. User Experience (UX) Heuristics
-   [ ] **Latency**: The UI should not freeze for more than 200ms. Long operations must show a loading spinner (`is_processing` state).
-   [ ] **Clarity**: Error messages (e.g., "API Key Invalid") must be shown in the UI, not just the console log.
-   [ ] **Navigation**: It should be impossible to get "stuck" in a view (Back buttons or Breadcrumbs must always work).
