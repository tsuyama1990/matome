# Cycle 02 User Acceptance Testing (UAT) Plan

## 1. Test Scenarios

### Scenario 05: Embedding Vector Generation (Priority: High)
*   **Goal**: Ensure that text chunks are correctly converted to vector representations.
*   **Inputs**: A list of `Chunk` objects containing "This is a test." and "Another sentence."
*   **Expected Outcome**: Each chunk's `embedding` field is populated with a `List[float]` of length 1024 (E5-large dimension).
*   **Mock Mode**: Use `np.random.rand(1024)` to simulate embeddings without loading the model.

### Scenario 06: Clustering Logic Verification (Priority: High)
*   **Goal**: Ensure that semantically similar chunks are grouped together.
*   **Inputs**:
    *   3 chunks related to "Apple Pie Recipe".
    *   3 chunks related to "Python Programming".
*   **Expected Outcome**:
    *   The clustering engine returns 2 distinct clusters.
    *   Chunks 0-2 are in Cluster A.
    *   Chunks 3-5 are in Cluster B.

### Scenario 07: Single Cluster Edge Case (Priority: Low)
*   **Goal**: Ensure the system handles small inputs gracefully.
*   **Inputs**: A single chunk.
*   **Expected Outcome**: The clustering engine returns 1 cluster containing that single chunk.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Semantic Clustering

  Scenario: Creating embeddings for chunks
    GIVEN a list of text chunks
    WHEN the EmbeddingService processes the list
    THEN each chunk should have a non-empty embedding vector
    AND all vectors should have the same dimension

  Scenario: Grouping similar topics
    GIVEN a set of vectors representing two distinct topics
    WHEN the ClusterEngine performs clustering
    THEN it should identify at least 2 clusters
    AND vectors from the same topic should belong to the same cluster

  Scenario: Determining optimal cluster count
    GIVEN a set of vectors with clear separation into 3 groups
    WHEN the ClusterEngine calculates the optimal number of clusters (BIC)
    THEN the result should be close to 3
```
