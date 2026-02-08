# Cycle 04 Specification: Recursive Summarization (RAPTOR)

## 1. Summary

Cycle 04 is the integration phase where the individual components—chunking, embedding, clustering, and summarization—are orchestrated into a coherent whole. We implement the **RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)** algorithm. This engine takes the initial chunks, clusters them, summarizes each cluster, and then recursively treats these summaries as new "chunks" for the next level of clustering. This process continues until a single root node (the overall summary) is produced, resulting in a hierarchical tree structure that captures both high-level themes and granular details.

## 2. System Architecture

The core orchestration logic resides in `raptor.py`.

```
.
├── dev_documents/
├── src/
│   └── matome/
│       ├── domain/
│       │   └── **models.py**   # DocumentTree, SummaryNode
│       ├── engines/
│       │   ├── **raptor.py**   # The Main Loop
│       │   └── ...
│       └── exporters/
│           ├── __init__.py
│           └── **markdown.py** # Initial plain text exporter
├── tests/
│   └── **test_raptor.py**
└── pyproject.toml
```

## 3. Design Architecture

### 3.1. Domain Models (`src/matome/domain/models.py`)

*   **`SummaryNode`**:
    *   `id`: `str` (UUID)
    *   `text`: `str` (The summary content)
    *   `level`: `int` (0 = leaf summaries, 1 = parent summaries, etc.)
    *   `children_indices`: `List[int]` (Indices of chunks if level 0)
    *   `children_node_ids`: `List[str]` (IDs of child SummaryNodes if level > 0)
*   **`DocumentTree`**:
    *   `root_node`: `SummaryNode`
    *   `all_nodes`: `Dict[str, SummaryNode]`
    *   `leaf_chunks`: `List[Chunk]`

### 3.2. RAPTOR Engine (`src/matome/engines/raptor.py`)

*   **Class**: `RaptorEngine`
*   **Method**: `run(text: str) -> DocumentTree`
    1.  **Level 0**: `Chunker.split_text(text)`.
    2.  **Loop**:
        *   `Embedder.embed(current_nodes)`
        *   `ClusterEngine.cluster(current_nodes)`
        *   For each cluster:
            *   Gather text from children.
            *   `SummarizationAgent.summarize(text)`.
            *   Create new `SummaryNode`.
        *   If only 1 node remains (Root), break.
        *   Else, `current_nodes = new_nodes`.
    3.  **Return**: `DocumentTree`.

### 3.3. Markdown Exporter (`src/matome/exporters/markdown.py`)

*   **Function**: `export_to_markdown(tree: DocumentTree) -> str`
    *   Traverses the tree (DFS or BFS) and prints summaries with indentation or headings corresponding to their level.

## 4. Implementation Approach

1.  **Model Definition**:
    *   Update `models.py` to include `SummaryNode` and `DocumentTree`.
2.  **Engine Logic**:
    *   Implement `RaptorEngine`.
    *   Ensure the loop handles the base case (Leaf Chunks) and recursive case (Summary Nodes) correctly—they both need `text` and `embedding` interfaces.
    *   Implement a check to prevent infinite loops (e.g., if clustering returns `n_clusters == n_input`, force merge or stop).
3.  **Integration**:
    *   Inject `Chunker`, `Embedder`, `ClusterEngine`, `SummarizationAgent` as dependencies into `RaptorEngine`.
4.  **Exporter**:
    *   Implement a simple `to_markdown` function to visualize the tree structure textually.

## 5. Test Strategy

### 5.1. Unit Testing
*   **Target**: `src/matome/engines/raptor.py`
    *   **Test Case**: Mock the `ClusterEngine` to always return 1 cluster for 5 items. Verify the loop runs exactly once (5 items -> 1 summary -> Root).
    *   **Test Case**: Mock the `ClusterEngine` to return 2 clusters for 10 items, then 1 cluster for those 2 summaries. Verify the tree has depth 2.

### 5.2. Integration Testing (Mock Mode)
*   **Scenario**:
    *   Run `RaptorEngine.run()` with a short dummy text ("A. B. C. D. E.").
    *   Verify that a `DocumentTree` is returned.
    *   Verify that the Root Node text contains "Summary of...".
