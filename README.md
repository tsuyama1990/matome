# Matome: Long Context Summarization System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome** is a next-generation document processing platform that solves the "Lost-in-the-Middle" problem in Large Language Models. By combining **Recursive Abstractive Processing (RAPTOR)** with **Japanese-optimized Semantic Chunking**, it transforms massive documents into structured, navigable, and verifiable knowledge trees.

## Overview

Traditional RAG systems often split text arbitrarily, breaking sentences and losing context. Matome employs a "System Engineering" approach, starting with a robust **Japanese Semantic Chunker** that respects linguistic boundaries (punctuation, quotes) to preserve narrative flow before summarization begins.

## Features

*   **Recursive Summarization (RAPTOR)**: Builds a hierarchical tree of summaries from leaf chunks to a root node, capturing both high-level themes and granular details.
*   **Intelligent Clustering**: Uses **UMAP** and **Gaussian Mixture Models (GMM)** to group semantically similar chunks for coherent summarization.
*   **Summarization Agent**: Intelligent summarization using **Chain of Density (CoD)** prompting to create high-density, entity-rich summaries via OpenRouter (supporting **Gemini 1.5 Flash**, **GPT-4o**).
*   **Japanese-Optimized Semantic Chunking**: Intelligently splits text at sentence boundaries (using punctuation like `。`, `！`, `？`) and merges them into semantically coherent chunks based on token limits.
*   **Markdown Export**: Exports the generated knowledge tree to a hierarchical Markdown format for easy reading and navigation.
*   **Type-Safe Architecture**: Built with strict Pydantic models for reliable data handling.

## Requirements

*   **Python 3.11+**
*   **UV** (Recommended) or pip for dependency management.
*   **OpenRouter API Key** (for summarization features)

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

### 1. Basic Text Chunking

```python
from matome.engines.chunker import JapaneseSemanticChunker
from domain_models.config import ProcessingConfig

# Initialize chunker & config
chunker = JapaneseSemanticChunker(model_name="cl100k_base")
config = ProcessingConfig(max_tokens=500)

# Process text
raw_text = "これは長い文章です。ここで文が終わります。次の文が始まります。"
chunks = chunker.split_text(raw_text, config)

for chunk in chunks:
    print(f"Chunk {chunk.index}: {chunk.text}")
```

### 2. Full RAPTOR Pipeline (Recursive Summarization)

```python
from matome import RaptorEngine, export_to_markdown
from matome.engines.chunker import JapaneseSemanticChunker
from matome.engines.embedder import EmbeddingService
from matome.engines.cluster import GMMClusterer
from matome.agents.summarizer import SummarizationAgent
from domain_models.config import ProcessingConfig

# 1. Initialize Components
config = ProcessingConfig()
chunker = JapaneseSemanticChunker(config)
embedder = EmbeddingService(config)
clusterer = GMMClusterer()
summarizer = SummarizationAgent(config)

# 2. Create Engine
engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

# 3. Run Pipeline
text = "Your long document here..."
tree = engine.run(text)

# 4. Export Result
markdown_output = export_to_markdown(tree)
print(markdown_output)
```

## Architecture/Structure

The project uses a clean architecture with separate domain models and processing engines.

```
src/
├── domain_models/      # Data definitions (Document, Chunk, Config)
└── matome/             # Core logic
    ├── agents/         # AI Agents (Summarizer)
    ├── engines/        # Processing engines (Chunker, Clusterer, RAPTOR)
    ├── exporters/      # Output formatters (Markdown)
    └── utils/          # Text processing utilities
```

## Roadmap

*   **Obsidian Export**: Visualizing the knowledge tree.
*   **CLI**: Command-line interface for easy file processing.
*   **Verification Module**: Chain of Verification (CoVe) for hallucination detection.
