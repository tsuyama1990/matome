# Matome: Long Context Summarization System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome** is a next-generation document processing platform that solves the "Lost-in-the-Middle" problem in Large Language Models. By combining **Recursive Abstractive Processing (RAPTOR)** with **Japanese-optimized Semantic Chunking**, it transforms massive documents into structured, navigable, and verifiable knowledge trees.

## Overview

Traditional RAG systems often split text arbitrarily, breaking sentences and losing context. Matome employs a "System Engineering" approach, starting with a robust **Japanese Semantic Chunker** that respects linguistic boundaries (punctuation, quotes) to preserve narrative flow before summarization begins.

## Features

*   **Japanese-Optimized Semantic Chunking**: Intelligently splits text at sentence boundaries (using punctuation like `。`, `！`, `？`) and merges them into semantically coherent chunks based on token limits.
*   **Semantic Vectorization**: Generates high-quality vector embeddings using `multilingual-e5-large`.
*   **Intelligent Clustering**: Groups semantically similar chunks using UMAP dimensionality reduction and GMM (Gaussian Mixture Models) for hierarchical summarization.
*   **Text Normalization**: Automatically handles full-width/half-width character normalization (NFKC) for consistent processing.
*   **Type-Safe Architecture**: Built with strict Pydantic models for reliable data handling.

## Requirements

*   **Python 3.11+**
*   **UV** (Recommended) or pip for dependency management.

## Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/matome.git
    cd matome
    ```

2.  **Install dependencies**
    Using `uv` (recommended):
    ```bash
    uv sync
    ```
    Or using `pip`:
    ```bash
    pip install .
    ```

## Usage

Matome provides a Python API for text chunking, embedding, and clustering.

### Basic Chunking

```python
from matome.engines import JapaneseSemanticChunker
from domain_models.config import ProcessingConfig

# 1. Initialize the chunker
chunker = JapaneseSemanticChunker(model_name="cl100k_base")

# 2. Define configuration (e.g., max 500 tokens per chunk)
config = ProcessingConfig(max_tokens=500)

# 3. Process text
raw_text = "これは長い文章です。ここで文が終わります。次の文が始まります。"
chunks = chunker.split_text(raw_text, config)

# 4. Inspect results
for chunk in chunks:
    print(f"Chunk {chunk.index}: {chunk.text}")
```

### Embedding and Clustering

```python
import numpy as np
from matome.engines import JapaneseSemanticChunker, EmbeddingService, ClusterEngine
from domain_models.config import ProcessingConfig

# 1. Config
config = ProcessingConfig()

# 2. Chunking
chunker = JapaneseSemanticChunker()
text = "This is a sample text for clustering. It will be split into chunks."
chunks = chunker.split_text(text, config)

# 3. Embedding
embedder = EmbeddingService()
chunks_with_embeddings = embedder.embed_chunks(chunks)

# 4. Clustering
cluster_engine = ClusterEngine(config)
# Extract embeddings as numpy array
embeddings = np.array([c.embedding for c in chunks_with_embeddings])
clusters = cluster_engine.perform_clustering(chunks_with_embeddings, embeddings)

for cluster in clusters:
    print(f"Cluster {cluster.id}: {cluster.node_indices}")
```

## Architecture/Structure

The project uses a clean architecture with separate domain models and processing engines.

```
src/
├── domain_models/      # Data definitions (Document, Chunk, Config)
└── matome/             # Core logic
    ├── engines/        # Processing engines (Chunker)
    └── utils/          # Text processing utilities
```

## Roadmap

*   **Summarization Agent**: Generating recursive summaries using LLMs.
*   **Obsidian Export**: Visualizing the knowledge tree.
*   **CLI**: Command-line interface for easy file processing.
