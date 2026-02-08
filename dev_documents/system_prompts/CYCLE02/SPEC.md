# Cycle 02 Specification: Embeddings & Clustering Core

## 1. Summary

In this cycle, we implement the mathematical core of the summarization system: vectorization and clustering. The system needs to understand the semantic similarity between text chunks to group them effectively. We will integrate `multilingual-e5-large` for generating high-quality embeddings and use a combination of UMAP (Uniform Manifold Approximation and Projection) and GMM (Gaussian Mixture Models) to identify thematic clusters within the document. This forms the basis of the RAPTOR tree structure.

## 2. System Architecture

Files related to embedding and clustering are added/modified.

```
.
├── dev_documents/
├── src/
│   └── matome/
│       ├── __init__.py
│       ├── config.py
│       ├── domain_models/
│       │   ├── __init__.py
│       │   └── **manifest.py**   # Updated Chunk with vector field
│       ├── engines/
│       │   ├── __init__.py
│       │   ├── chunker.py
│       │   ├── **embedder.py** # Wrapper for HuggingFace Embeddings
│       │   └── **cluster.py**  # UMAP + GMM Logic
│       └── utils/
│           └── ...
├── tests/
│   ├── **test_embedder.py**
│   └── **test_cluster.py**
└── pyproject.toml              # Added umap-learn, scikit-learn, sentence-transformers
```

## 3. Design Architecture

### 3.1. Updated Domain Models (`src/domain_models/manifest.py`)

*   **`Chunk`**:
    *   Add `embedding`: `list[float] | None` (The vector representation).
*   **`Cluster`**:
    *   `id`: `int` (Cluster Label)
    *   `node_indices`: `list[int | str]` (Indices of chunks/nodes belonging to this cluster)
    *   `level`: `int` (Hierarchy level in RAPTOR tree)

### 3.2. Embedding Service (`src/matome/engines/embedder.py`)

*   **Class**: `EmbeddingService`
*   **Method**: `embed_chunks(chunks: List[Chunk]) -> List[Chunk]`
    *   Uses `HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")`.
    *   Batches the requests to avoid OOM errors.
    *   Updates the `embedding` field of each chunk in-place or returns new objects.

### 3.3. Clustering Engine (`src/matome/engines/cluster.py`)

*   **Class**: `ClusterEngine`
*   **Method**: `perform_clustering(embeddings: np.ndarray, n_neighbors: int = 15, min_dist: float = 0.1) -> List[Cluster]`
    *   **Step 1: UMAP**: Reduce dimensions (e.g., to 2 or 5 components) to make GMM more effective.
    *   **Step 2: GMM (Gaussian Mixture Model)**:
        *   Determine optimal `n_components` (number of clusters) using BIC (Bayesian Information Criterion).
        *   Fit GMM on the reduced embeddings.
        *   Predict cluster labels (soft clustering is possible but hard assignment is simpler for V1).
    *   **Returns**: A list of `Cluster` objects, each containing indices of chunks.

## 4. Implementation Approach

1.  **Dependency Management**:
    *   Add `langchain-huggingface`, `sentence-transformers`, `umap-learn`, `scikit-learn`, `numpy` to `pyproject.toml`.
2.  **Model Update**:
    *   Update `Chunk` Pydantic model to include `embedding: Optional[List[float]] = None`.
3.  **Embedder Implementation**:
    *   Implement `EmbeddingService`. Use a singleton pattern or cached property for the model loader to avoid reloading large weights.
4.  **Clustering Implementation**:
    *   Implement `ClusterEngine`.
    *   Include a `_calculate_optimal_clusters` helper method that iterates through `n_components=2..20` and finds the minimum BIC.
5.  **Refactoring Chunker**:
    *   (Optional) Use embeddings to refine semantic chunk boundaries (Semnatic Chunking advanced mode), but for now, we stick to the regex-based chunker and just *add* embeddings to the output.

## 5. Test Strategy

### 5.1. Unit Testing
*   **Target**: `src/matome/engines/embedder.py`
    *   **Test Case**: Mock the `HuggingFaceEmbeddings` class. Verify that `embed_chunks` correctly populates the list.
*   **Target**: `src/matome/engines/cluster.py`
    *   **Test Case**: Provide a synthetic `numpy` array of 10 vectors (2 clear groups). Verify that GMM identifies 2 clusters.
    *   **Test Case**: Test edge case with only 1 chunk (should return 1 cluster or handle gracefully).

### 5.2. Integration Testing
*   **Scenario**:
    1.  Ingest `test_data/sample.txt`.
    2.  Chunk it (Cycle 01).
    3.  Embed it (Cycle 02).
    4.  Cluster it (Cycle 02).
    5.  **Verify**: The output is a list of `Cluster` objects, covering all input chunks.
