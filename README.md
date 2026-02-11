# Matome 2.0: Knowledge Installation

![Status](https://img.shields.io/badge/status-development-orange)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome** (Japanese for "Summary") is a next-generation summarization system that transforms passive reading into active "Knowledge Installation." Unlike traditional tools that merely compress text, Matome generates a hierarchical **DIKW (Data, Information, Knowledge, Wisdom)** structure, allowing users to zoom from high-level aphorisms down to concrete action items and original source evidence.

## Overview

-   **What:** A local-first, hierarchical summarization engine using the RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) methodology.
-   **Why:** To help users deeply understand complex documents by structuring content into levels of abstraction, from raw data to actionable wisdom.
-   **How:** It chunks text, embeds it, clusters related concepts, and recursively summarizes them using Large Language Models (LLMs).

## Features

-   **Hierarchical Summarization:** Generates a multi-level tree of summaries (Wisdom -> Knowledge -> Information -> Data).
-   **Source Verification:** Includes a verification agent that checks summaries against source text to detect hallucinations.
-   **Local Storage:** Uses SQLite and local file storage for processing artifacts, ensuring privacy and offline capability.
-   **Obsidian Export:** Exports the generated summary tree directly to Obsidian Canvas format for visual exploration.
-   **Markdown Export:** Generates a comprehensive Markdown report of the entire summary tree.

## Requirements

-   **Python 3.11+**
-   **OpenAI API Key** (or OpenRouter) for LLM access.
-   **uv** (recommended) or `pip` for dependency management.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-org/matome.git
    cd matome
    ```

2.  **Install dependencies (using uv):**
    ```bash
    uv sync
    ```
    *Or using pip:*
    ```bash
    pip install -e .[dev]
    ```

3.  **Configure Environment:**
    Create a `.env` file in the root directory:
    ```bash
    cp .env.example .env
    # Edit .env and add your OPENROUTER_API_KEY or OPENAI_API_KEY
    ```

## Usage

### CLI: Batch Generation
Process a text file to generate the DIKW tree and export results.

```bash
uv run matome run data/my_book.txt
```

**Options:**
-   `--output-dir`, `-o`: Directory to save results (default: `results`).
-   `--model`, `-m`: Summarization model (default: `openai/gpt-4o-mini`).
-   `--verify/--no-verify`: Enable/Disable hallucination verification (default: Enabled).

**Example:**
```bash
uv run matome run document.txt -o my_summary --model openai/gpt-4o
```

## Architecture

Matome is built with a modular architecture:

```ascii
src/
├── domain_models/       # Pydantic Schemas & Constants
├── matome/
│   ├── agents/          # LLM Agents & Prompt Strategies
│   ├── engines/         # RAPTOR & Clustering Logic
│   ├── exporters/       # Markdown & Obsidian Exporters
│   └── utils/           # Utilities (Store, IO, Text)
tests/                   # Unit, Integration & UAT Tests
```

## Roadmap

-   **Interactive GUI:** A Panel-based interface for exploring and refining summaries (Coming in Cycle 04).
-   **Semantic Zooming:** Enhanced navigation between DIKW levels.
-   **Advanced Refinement:** User-guided rewriting of specific nodes.

## License

MIT License. See `LICENSE` for details.
