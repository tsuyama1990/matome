# Matome: Long Context Summarization System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome** is a next-generation document processing platform that solves the "Lost-in-the-Middle" problem in Large Language Models. By combining **Recursive Abstractive Processing (RAPTOR)** with **Japanese-optimized Semantic Chunking**, it transforms massive documents into structured, navigable, and verifiable knowledge trees.

## Overview

Traditional RAG systems often split text arbitrarily, breaking sentences and losing context. Matome employs a "System Engineering" approach, starting with a robust **Japanese Semantic Chunker** that respects linguistic boundaries (punctuation, quotes) to preserve narrative flow before summarization begins.

## Features

*   **Summarization Agent**: Intelligent summarization using **Chain of Density (CoD)** prompting to create high-density, entity-rich summaries.
*   **OpenRouter Integration**: Seamlessly connect to state-of-the-art LLMs (like **Gemini 1.5 Flash**, **GPT-4o**) via OpenRouter.
*   **Japanese-Optimized Semantic Chunking**: Intelligently splits text at sentence boundaries (using punctuation like `。`, `！`, `？`) and merges them into semantically coherent chunks based on token limits.
*   **Text Normalization**: Automatically handles full-width/half-width character normalization (NFKC) for consistent processing.
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

### 1. Text Chunking

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

### 2. Summarization

```python
from matome.agents.summarizer import SummarizationAgent
from domain_models.config import ProcessingConfig

# Initialize agent (uses OPENROUTER_API_KEY from env)
agent = SummarizationAgent(model_name="google/gemini-flash-1.5")
config = ProcessingConfig()

# Summarize context
context = "Deep learning is a subset of machine learning..."
summary = agent.summarize(context, config)

print(f"Summary: {summary}")
```

## Architecture/Structure

The project uses a clean architecture with separate domain models and processing engines.

```
src/
├── domain_models/      # Data definitions (Document, Chunk, Config)
└── matome/             # Core logic
    ├── agents/         # AI Agents (Summarizer)
    ├── engines/        # Processing engines (Chunker, Clusterer)
    └── utils/          # Text processing utilities
```

## Roadmap

*   **Embedding & Clustering**: Grouping chunks by semantic similarity.
*   **RAPTOR Logic**: Recursive summarization tree building.
*   **Obsidian Export**: Visualizing the knowledge tree.
*   **CLI**: Command-line interface for easy file processing.
