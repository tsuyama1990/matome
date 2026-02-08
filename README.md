# Matome: Long Context Summarization System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome** is a next-generation document processing platform that solves the "Lost-in-the-Middle" problem in Large Language Models. By combining **Recursive Abstractive Processing (RAPTOR)** with **Japanese-optimized Semantic Chunking**, it transforms massive documents into structured, navigable, and verifiable knowledge trees.

## Overview

Traditional RAG systems often split text arbitrarily, breaking sentences and losing context. Matome employs a "System Engineering" approach, starting with a robust **Japanese Semantic Chunker** that respects linguistic boundaries (punctuation, quotes) to preserve narrative flow before summarization begins.

## Features

*   **Japanese-Optimized Semantic Chunking**: Intelligently splits text at sentence boundaries (using punctuation like `。`, `！`, `？`) and merges them into semantically coherent chunks based on token limits.
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

Currently, Matome provides a Python API for text chunking.

```python
from matome.engines.chunker import JapaneseSemanticChunker
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

*   **Embedding & Clustering**: Grouping chunks by semantic similarity.
*   **Summarization Agent**: Generating recursive summaries using LLMs.
*   **Obsidian Export**: Visualizing the knowledge tree.
*   **CLI**: Command-line interface for easy file processing.
