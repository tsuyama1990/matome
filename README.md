# Matome 2.0: Knowledge Installation System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Transform static documents into structured knowledge with semantic zooming.**

## Overview

**Matome** is an advanced summarization system designed to process long-form text using the RAPTOR algorithm. It breaks down complex documents into a hierarchy of summaries, enabling users to navigate from high-level "Wisdom" down to granular "Data".

Why use Matome?
*   **Handle Long Contexts:** Process entire books or reports that exceed typical LLM context windows.
*   **Structured Knowledge:** Unlike flat summaries, Matome builds a tree of knowledge nodes.
*   **Extensible Architecture:** Designed with the Strategy Pattern to support custom summarization logic and future interactive refinements.

## Features

*   **Recursive Summarization (RAPTOR):** Automatically chunks, embeds, clusters, and summarizes text recursively.
*   **Strategy Pattern Engine:** Decoupled prompt logic allows swapping summarization strategies (e.g., Chain of Density) without changing core code.
*   **Enhanced Metadata Schema:** Every summary node tracks its Semantic Level (DIKW: Data, Information, Knowledge, Wisdom) and edit history.
*   **Robust Persistence:** Uses SQLite for efficient storage and retrieval of large document trees.
*   **CLI Interface:** Simple command-line tool for batch processing.

## Requirements

*   **Python 3.11+**
*   **uv** (Recommended) or `pip`
*   **OpenAI API Key** (or OpenRouter)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/matome.git
    cd matome
    ```

2.  **Install dependencies:**
    Using `uv` (faster):
    ```bash
    uv sync
    ```
    Using `pip`:
    ```bash
    pip install .
    ```

3.  **Configure Environment:**
    Set your API key (e.g., in `.env` or export):
    ```bash
    export OPENROUTER_API_KEY=sk-...
    # Or for testing:
    export OPENROUTER_API_KEY=mock
    ```

## Usage

### Basic Run
Process a text file and generate a summary tree.

```bash
# Using uv run ensures dependencies are loaded
uv run matome run path/to/your/document.txt
```

### Specify Model
You can choose a specific LLM model (supported by LiteLLM/LangChain).

```bash
uv run matome run document.txt --model openai/gpt-4o
```

The output `chunks.db` and `summary.md` will be saved in the `results/` directory.

## Architecture

```ascii
src/matome/
├── agents/         # LLM Agents (Summarizer, Verifier) & Strategies
├── engines/        # Core Logic (RAPTOR, Chunker, Clusterer)
├── utils/          # Database (DiskChunkStore) & Helpers
└── cli.py          # Command Line Interface

src/domain_models/  # Pydantic Schemas (Node, Metadata)
```

## Roadmap

*   **Cycle 02:** DIKW Generation Engine (Semantic Zooming)
*   **Cycle 03:** Interactive Refinement & GUI Foundation
*   **Cycle 04:** Advanced Clustering & Visualization
