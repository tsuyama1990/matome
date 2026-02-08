# Architectural Analysis

## 1. Overview
This document records the architectural analysis performed on the `matome` repository to align the implementation with the initial specification (`ALL_SPEC.md`) and pragmatic development needs.

## 2. Discrepancies Found

### 2.1 Scope Mismatch
- **Spec**: Describes a full RAPTOR system including Embeddings, Clustering (GMM/UMAP), Summarization (OpenRouter), and Tree-based retrieval.
- **Implementation**: Currently only contains a `JapaneseSemanticChunker` which performs chunking.
- **Decision**: The "Refactoring" task implies stabilizing the current code but also establishing the correct architecture for the full system. I will add the missing domain models and interfaces to guide future implementation, even if the full logic isn't implemented in this session.

### 2.2 Naming & Logic Mismatch in Chunker
- **Spec**: Requires "Semantic Chunking" using `langchain_experimental.text_splitter.SemanticChunker` and `multilingual-e5-large` embeddings.
- **Implementation**: The class `JapaneseSemanticChunker` uses `tiktoken` and regex-based sentence splitting. It groups sentences by token count, not by semantic similarity.
- **Analysis**: The current implementation is robust and fast (Pragmatic), but the name `SemanticChunker` is misleading. It is effectively a "Recursive Token Chunker" or "Sentence Grouper".
- **Decision**: Rename the existing class to `JapaneseTokenChunker`. This prioritizes the *reality* of the code (it works as a token chunker) over the *spec* (which asked for semantic). I will also create a `Chunker` interface to allow for a future `JapaneseSemanticChunker` implementation that matches the spec.

### 2.3 Missing Domain Models
- **Spec**: Defines concepts like `Cluster`, `Summary`, `Tree`, `Node`.
- **Implementation**: Only `Document` and `Chunk` exist.
- **Decision**: Add `Cluster`, `SummaryNode`, and `Tree` to `src/domain_models/manifest.py` to support the RAPTOR architecture.

### 2.4 Missing Interfaces
- **Spec**: Implies a pipeline of `Chunking -> Embedding -> Clustering -> Summarization`.
- **Implementation**: No interfaces defined.
- **Decision**: Create `src/matome/interfaces.py` defining `Chunker`, `Clusterer`, and `Summarizer` protocols.

## 3. Plan of Action
1.  **Refactor Schema**: Update `src/domain_models` with missing models.
2.  **Refactor Chunker**: Rename `JapaneseSemanticChunker` to `JapaneseTokenChunker`.
3.  **Define Contracts**: Add `interfaces.py`.
4.  **Update Tests**: Align tests with the new naming and models.
