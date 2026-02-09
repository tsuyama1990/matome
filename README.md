# Matome: Long Context Summarization System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome** is a next-generation document processing platform that solves the "Lost-in-the-Middle" problem in Large Language Models. By combining **Recursive Abstractive Processing (RAPTOR)** with **Japanese-optimized Semantic Chunking**, it transforms massive documents into structured, navigable, and verifiable knowledge trees.

## Overview

Traditional RAG systems often split text arbitrarily, breaking sentences and losing context. Matome employs a "System Engineering" approach, starting with a robust **Japanese Semantic Chunker** that respects linguistic boundaries (punctuation, quotes) to preserve narrative flow before summarization begins. It then recursively summarizes content into a hierarchical tree and verifies the results against the source text to minimize hallucinations.

## Features

*   **Recursive Summarization (RAPTOR)**: Builds a hierarchical tree of summaries from leaf chunks to a root node, capturing both high-level themes and granular details.
*   **Hallucination Verification**: Uses a dedicated **Verifier Agent** to cross-check generated summaries against the source text, flagging unsupported claims with a confidence score.
*   **Intelligent Clustering**: Uses **UMAP** and **Gaussian Mixture Models (GMM)** to group semantically similar chunks for coherent summarization.
*   **Command Line Interface (CLI)**: Easy-to-use `matome` command for running the full pipeline on text files with progress tracking.
*   **Obsidian Canvas Export**: Exports the generated knowledge tree to an **Obsidian Canvas** (`.canvas`) file, allowing for visual inspection and reorganization (KJ Method).
*   **Markdown Export**: Exports the generated knowledge tree to a hierarchical Markdown format.
*   **Japanese-Optimized Chunking**: Intelligently splits text at sentence boundaries and merges them into semantically coherent chunks.
*   **Type-Safe Architecture**: Built with strict Pydantic models for reliable data handling.

## Requirements

*   **Python 3.11+**
*   **UV** (Recommended) or pip.
*   **OpenRouter API Key** (for summarization and verification).

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

3.  **Configure Environment**
    Set your OpenRouter API key:
    ```bash
    export OPENROUTER_API_KEY="your_key_here"
    ```

## Usage

### Command Line Interface (CLI)

Matome provides a robust CLI to process documents.

1.  **Run the Pipeline**:
    Process a text file, generate summaries, verify them, and export results.
    ```bash
    uv run matome run input.txt --output-dir results
    ```

    **Options**:
    *   `--model`: Summarization model (default: `openai/gpt-4o-mini`).
    *   `--verifier-model`: Verification model (default: `openai/gpt-4o-mini`).
    *   `--verify / --no-verify`: Enable or disable verification step (default: enabled).
    *   `--max-tokens`: Maximum tokens per chunk (default: 500).

2.  **Check Results**:
    The output directory will contain:
    *   `summary_all.md`: Full hierarchical summary.
    *   `summary_kj.canvas`: Visual knowledge graph for Obsidian.
    *   `verification_result.json`: Detailed verification report.
    *   `chunks.db`: SQLite database containing all chunks and embeddings.

### Python API

```python
from pathlib import Path
from matome.engines.semantic_chunker import JapaneseSemanticChunker
from matome.engines.embedder import EmbeddingService
from matome.engines.cluster import GMMClusterer
from matome.agents.summarizer import SummarizationAgent
from matome.agents.verifier import VerifierAgent
from matome.engines.raptor import RaptorEngine
from matome.utils.store import DiskChunkStore
from domain_models.config import ProcessingConfig

# 1. Configuration
config = ProcessingConfig(max_tokens=500)

# 2. Initialize Components
embedder = EmbeddingService(config)
chunker = JapaneseSemanticChunker(embedder)
clusterer = GMMClusterer()
summarizer = SummarizationAgent(config)
verifier = VerifierAgent(config)

# 3. Run RAPTOR Pipeline
store = DiskChunkStore()
engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)
tree = engine.run("Your long Japanese text here...", store=store)

# 4. Verify Root Summary
if tree.root_node:
    root_summary = tree.root_node.text
    result = verifier.verify(root_summary, "Source text...")
    print(f"Verification Score: {result.score}")
```

## Architecture/Structure

```
src/
├── domain_models/      # Data definitions (Document, Chunk, Config, Verification)
└── matome/             # Core logic
    ├── agents/         # AI Agents (Summarizer, Verifier)
    ├── engines/        # Processing engines (Chunker, Clusterer, RAPTOR)
    ├── exporters/      # Output formatters (Markdown, Obsidian Canvas)
    ├── utils/          # Utilities (Store, IO, Text)
    └── cli.py          # Command Line Interface
```
