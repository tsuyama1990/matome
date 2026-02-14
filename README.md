# Matome 2.0: Knowledge Installation System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome 2.0** is an interactive "Knowledge Installation" system that transforms long-form text into a structured DIKW (Data, Information, Knowledge, Wisdom) hierarchy. Unlike static summarizers, it allows you to explore information at varying levels of abstraction—from philosophical wisdom down to actionable checklists—and interactively refine the content to match your mental model.

## Features

-   **DIKW Generation (Strategy Pattern):**
    -   **Wisdom (Level 1):** Generates abstract, philosophical insights (Root Node).
    -   **Knowledge (Level 2):** Synthesizes frameworks and mental models (Intermediate Nodes).
    -   **Information (Level 3):** Extracts actionable checklists and steps (Leaf Summaries).
-   **Semantic Zooming:** Navigate documents like a map, zooming from "Big Idea" to "Evidence".
-   **Traceability:** Every summary links back to source chunks ("Data").
-   **Scalability:** Uses streaming processing and disk-based storage (`SQLite`) to handle large documents without memory overflows.
-   **Local First:** Your data stays on your machine (except for LLM calls).

## Prerequisites

-   **Python 3.11+**
-   **uv** (Package manager)
-   **OpenRouter / OpenAI API Key** (Set as `OPENROUTER_API_KEY` env var)

## Installation

```bash
git clone https://github.com/your-org/matome.git
cd matome
uv sync
```

## Usage

### 1. Generate a DIKW Tree

Process a raw text file into a structured knowledge base.

```bash
# Standard DIKW Generation
uv run matome run input.txt --mode dikw

# Customize output directory
uv run matome run input.txt --mode dikw --output-dir my_results
```

**Options:**
-   `--mode dikw`: Activates the Wisdom/Knowledge/Information strategy.
-   `--mode default`: Uses standard summarization.
-   `--no-verify`: Skip the verification step (faster).

### 2. View Results

Matome exports results in multiple formats:
-   `summary_all.md`: A readable Markdown file organized by hierarchy.
-   `summary_kj.canvas`: An [Obsidian Canvas](https://obsidian.md/canvas) file for visual exploration.
-   `chunks.db`: A SQLite database containing the full tree structure.

## Architecture

```
matome/
├── src/
│   ├── domain_models/  # Pydantic schemas (DIKWLevel, SummaryNode)
│   ├── matome/
│   │   ├── agents/     # SummarizationAgent with Strategy Pattern
│   │   ├── engines/    # Scalable RaptorEngine (Streaming)
│   │   ├── ui/         # Panel GUI (Future Cycle)
│   │   └── utils/      # DiskChunkStore (SQLite)
```

## Development

**Running Tests:**
```bash
uv run pytest
```

**Code Quality:**
```bash
uv run ruff check .
uv run mypy .
```
