# Final User Acceptance Test & Tutorial Plan

## 1. Tutorial Strategy

To ensure that **Matome 2.0** delivers on its promise of "Knowledge Installation," we will provide a set of executable Jupyter Notebooks that guide users through the core features. These tutorials serve a dual purpose: they educate new users and act as rigorous User Acceptance Tests (UAT) for the system.

### "Mock Mode" for Reproducibility
A key challenge in AI development is the variability of LLM outputs. To address this, we will implement a "Mock Mode" for our tutorials.
- **Real Mode**: Uses actual API keys (OpenRouter/OpenAI) to generate fresh summaries. Used for personal exploration.
- **Mock Mode**: Uses pre-generated data stored in `tests/data/mock_responses/`. When the API key is set to a dummy value (e.g., "mock"), the system bypasses the LLM and returns deterministic, high-quality responses. This allows users (and CI systems) to experience the "Aha!" moment without incurring costs or waiting for generation.

### Target Persona
The tutorials are designed for a "Knowledge Worker" who is overwhelmed by information—a researcher, investor, or student who needs to grasp complex topics quickly.

## 2. Notebook Plan

We will create two primary notebooks in the `tutorials/` directory.

### `tutorials/01_quickstart.ipynb`: The "Aha! Moment"
**Objective**: Demonstrate the power of **Wisdom Extraction (L1)** in under 30 seconds.
**Scenario**: The user inputs a dense financial text (`test_data/エミン流「会社四季報」最強の読み方.txt`).
**Steps**:
1.  **Initialize**: Setup the environment (install dependencies).
2.  **Load Data**: Read the text file.
3.  **Run Pipeline (Mock Mode)**: Execute `matome.cli` with `--mode dikw`.
4.  **The Reveal**: Display the single-sentence "Wisdom" (L1).
    - *Expected Output*: "Market distortions appear only in 15-year fixed-point observations; ignore short-term noise." (or similar).
5.  **Validation**: Verify that the output is concise (<50 chars) and abstract.

### `tutorials/02_semantic_zooming.ipynb`: Interactive Knowledge Discovery
**Objective**: Demonstrate **Semantic Zooming (L2-L3)** and **Interactive Refinement**.
**Scenario**: The user wants to understand *why* the Wisdom is true and *how* to apply it.
**Steps**:
1.  **Load Previous Result**: Load the `chunks.db` generated in Tutorial 01.
2.  **Initialize Engine**: Create an `InteractiveRaptorEngine` instance.
3.  **Drill Down (Zoom In)**:
    - Programmatically select the Root Node.
    - Retrieve its children (Knowledge Layer).
    - Display them as a structured list.
    - *Expected Output*: "Mechanism 1: Time Arbitrage", "Mechanism 2: PSR Contrarianism".
4.  **Refine Node (Chat)**:
    - Select a specific "Action" node (L3).
    - Send a refinement instruction: "Rewrite this for a high school student using a sports analogy."
    - *Expected Output*: The node text updates to explain PSR using a "batting average" or "popularity contest" analogy.
5.  **Verify Traceability**:
    - Call `get_source_chunks(node_id)` to see the original text evidence.

## 3. Validation Steps for QA Agent

When running these notebooks (or their script equivalents), the QA process must verify the following:

### Validation for Tutorial 01 (Wisdom)
- [ ] **Execution**: Runs without error using "mock" API key.
- [ ] **Output format**: Result is a single string, not a list or JSON.
- [ ] **Content Quality**: The Wisdom string length is between 20 and 100 characters. It does not contain bullet points.
- [ ] **File Creation**: `results/summary_dikw.md` and `results/chunks.db` are created.

### Validation for Tutorial 02 (Zooming)
- [ ] **State Loading**: Successfully connects to the existing `chunks.db`.
- [ ] **Hierarchy Integrity**:
    - The Root node has `metadata.dikw_level == "wisdom"`.
    - Child nodes have `metadata.dikw_level == "knowledge"`.
    - Leaf nodes (before chunks) have `metadata.dikw_level == "information"`.
- [ ] **Refinement Persistence**:
    - After calling `engine.refine_node(id, instruction)`, the `node.text` changes.
    - `node.metadata.refinement_history` contains the instruction string.
    - The change is persisted to `chunks.db` (re-loading the DB shows the new text).
- [ ] **Concurrency**: No "Database Locked" errors occur during rapid read/write operations.
