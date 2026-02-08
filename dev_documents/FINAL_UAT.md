# Final User Acceptance Testing (UAT) Plan

## 1. Tutorial Strategy

The primary goal of this UAT plan is to validate the **Long Context Summarization System**'s ability to process lengthy documents into structured, verifiable summaries. We will achieve this through a series of interactive Jupyter Notebooks that serve both as test cases and as tutorials for new users.

### 1.1. Dual-Mode Testing
To ensure the system is robust and testable without incurring constant API costs, all tutorials will support two modes:
*   **Mock Mode (CI/Default)**: Uses pre-computed embeddings and dummy LLM responses. This allows the logic (chunking, clustering, tree building) to be tested in continuous integration environments.
*   **Real Mode**: Requires an `OPENROUTER_API_KEY`. This runs the full pipeline with actual LLM calls (Gemini 1.5 Flash / DeepSeek V3) to generate real summaries.

### 1.2. The "Aha! Moment"
The core UAT scenario is based on processing the "Emin Style Company Shikiho Reading Method" text. The user should experience the "Aha!" moment when they see a 100-page equivalent document turned into a structured, navigable Obsidian Canvas map.

## 2. Notebook Plan

We will generate the following notebooks in the `tutorials/` directory.

### 2.1. `tutorials/01_quickstart.ipynb` (The Basics)
*   **Goal**: Demonstrate text ingestion and semantic chunking.
*   **Scenario**: Load a sample text, apply the Japanese-optimized regex splitter, and visualize the chunks.
*   **Key Features**:
    *   Loading `test_data/sample.txt`.
    *   Initializing `SemanticChunker`.
    *   Displaying the first 5 chunks to verify sentence boundaries.
*   **Mode**: Works in both Mock and Real modes (Mock uses random vectors if embedding is skipped).

### 2.2. `tutorials/02_clustering_deep_dive.ipynb` (The Engine)
*   **Goal**: Show how the system groups related information.
*   **Scenario**: Take the chunks from step 1, generate embeddings (E5-large), and run UMAP + GMM clustering.
*   **Key Features**:
    *   Visualizing the 2D projection of chunks.
    *   Showing which chunks belong to which cluster.
    *   Explaining the "Soft Clustering" concept (a chunk can belong to multiple topics).
*   **Mode**: Real mode required for meaningful embeddings (or load pre-saved vectors in Mock).

### 2.3. `tutorials/03_full_raptor_pipeline.ipynb` (The "Aha!" Moment)
*   **Goal**: Execute the full recursive summarization process.
*   **Scenario**:
    1.  Load `test_data/エミン流「会社四季報」最強の読み方.txt`.
    2.  Run `RaptorEngine.run()`.
    3.  Generate `summary_all.md`.
*   **Success Criteria**:
    *   The output markdown structure reflects the document's logical hierarchy.
    *   Key terms from the source text (e.g., "Market Cap", "PSR") are present.
*   **Mode**: Real mode strongly recommended.

### 2.4. `tutorials/04_kj_method_visualization.ipynb` (The Output)
*   **Goal**: Visualize the result in Obsidian Canvas format.
*   **Scenario**: Take the `DocumentTree` from the previous step and export it to `summary_kj.json` (Canvas format).
*   **Key Features**:
    *   Mapping nodes to canvas coordinates.
    *   Creating links between parent and child nodes.
    *   Instructions on how to open this file in Obsidian.
*   **Mode**: Works in both modes (Mock uses a dummy tree).

## 3. Validation Steps

The QA Agent (or human reviewer) should perform the following checks:

### 3.1. Automated Checks (Mock Mode)
1.  Run `pytest` to ensure all unit tests pass.
2.  Execute `tutorials/01_quickstart.ipynb` without an API key. It should complete without errors.
3.  Execute `tutorials/04_kj_method_visualization.ipynb` with dummy data. It should generate a valid JSON file.

### 3.2. Manual Checks (Real Mode)
1.  Set `OPENROUTER_API_KEY` in the environment.
2.  Run `tutorials/03_full_raptor_pipeline.ipynb` with the target text.
3.  **Content Verification**:
    *   Open `summary_all.md`.
    *   Check if the summary covers at least 70% of the topics mentioned in the book's Table of Contents (P8-18).
    *   Verify that Japanese sentences are natural and not cut off mid-sentence.
4.  **Structure Verification**:
    *   Open the generated `.canvas` file in Obsidian.
    *   Verify that related notes are grouped together visually.
    *   Verify that clicking a summary note reveals its child chunks (if implemented).

### 3.3. Performance Checks
*   **Time**: The full pipeline for the test file should complete within 10 minutes.
*   **Cost**: Monitor OpenRouter usage. It should be minimal (mostly Gemini 1.5 Flash).
