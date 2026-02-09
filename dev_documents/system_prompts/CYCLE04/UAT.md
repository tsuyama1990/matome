# Cycle 04 User Acceptance Testing (UAT) Plan

## 1. Test Scenarios

### Scenario 11: Single-Level Summarization (Priority: Medium)
*   **Goal**: Ensure the system handles short documents correctly (no recursion needed).
*   **Inputs**: A document with ~3 paragraphs (1 cluster).
*   **Expected Outcome**: The RAPTOR engine returns a tree with Depth 1 (Root -> Chunks).

### Scenario 12: Multi-Level Tree Construction (Priority: High)
*   **Goal**: Ensure the recursive logic builds a hierarchy for long documents.
*   **Inputs**: A document with ~50 paragraphs (enough for multiple clusters).
*   **Expected Outcome**: The RAPTOR engine returns a tree with Depth >= 2 (Root -> Intermediate Summaries -> Chunks).

### Scenario 13: Summary Coherence Check (Priority: High)
*   **Goal**: Ensure the generated summary captures the main idea.
*   **Inputs**: A text about "Climate Change Impacts".
*   **Expected Outcome**: The Root Node summary mentions "Global Warming", "Sea Level Rise", and "Extreme Weather". (Use Mock LLM keywords or Real Mode).

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Recursive Summarization (RAPTOR)

  Scenario: Processing a short document
    GIVEN a document that fits within one cluster
    WHEN the RaptorEngine processes the document
    THEN it should generate a single summary node
    AND link all chunks directly to this node

  Scenario: Processing a long document
    GIVEN a document that spans multiple clusters
    WHEN the RaptorEngine processes the document
    THEN it should generate intermediate summary nodes for each cluster
    AND recursively summarize those nodes until a single root is reached
    AND the result should be a hierarchical tree structure
```
