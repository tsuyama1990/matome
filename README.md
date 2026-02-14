# Matome 2.0: Knowledge Installation System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome 2.0** is an interactive "Knowledge Installation" system that transforms long-form text into a structured DIKW (Data, Information, Knowledge, Wisdom) hierarchy. Unlike static summarizers, it allows you to explore information at varying levels of abstraction—from philosophical wisdom down to actionable checklists—and interactively refine the content to match your mental model.

## Features

-   **DIKW Tree Generation:** Automatically generates a hierarchical summary tree where the root represents "Wisdom" (The Big Idea), intermediate nodes represent "Knowledge" (Frameworks), and leaf nodes represent "Information" (Actionable Steps).
-   **Semantic Zooming:** Navigate your documents like a map, zooming in and out of details.
-   **Configurable Strategies:** Choose between classic RAPTOR summarization ('basic') and the new DIKW pyramid ('dikw').
-   **Export Options:** Export your knowledge tree to Markdown or Obsidian Canvas for further exploration.
-   **Traceability:** Every piece of wisdom is linked back to the original text chunks ("Data"), ensuring source verification.

## Requirements

-   **Python 3.12+**
-   **uv** (Recommended package manager) or pip
-   **OpenAI API Key** (Set in `.env` or environment variable `OPENROUTER_API_KEY`/`OPENAI_API_KEY`)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-org/matome.git
    cd matome
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```

3.  **Configure Environment:**
    Create a `.env` file or set environment variables:
    ```bash
    export OPENROUTER_API_KEY="your-api-key"
    ```

## Usage

### Generate a DIKW Tree

Run the CLI to ingest a text file and generate the summary tree.

```bash
uv run matome run path/to/document.txt --mode dikw
```

Options:
-   `--mode dikw`: Use the DIKW strategy (Wisdom/Knowledge/Information).
-   `--mode basic`: Use standard RAPTOR summarization.
-   `--output-dir results`: Specify output directory (default: `results`).

### Export Results

The `run` command automatically exports results to the output directory:
-   `summary_all.md`: A full markdown summary.
-   `summary_kj.canvas`: An Obsidian Canvas file for visual exploration.
-   `chunks.db`: SQLite database containing the full tree structure.

## Architecture Structure

```
matome/
├── src/
│   ├── domain_models/      # Pydantic Data Models (SummaryNode, Chunk, NodeMetadata)
│   ├── matome/
│   │   ├── agents/         # AI Logic (SummarizationAgent, PromptStrategies)
│   │   ├── engines/        # Core Engines (RaptorEngine, Clusterer)
│   │   ├── exporters/      # Export Logic (Markdown, Obsidian)
│   │   └── utils/          # Utilities (Store, Prompts)
├── tests/                  # Test Suite (Unit, Integration, UAT)
└── dev_documents/          # Documentation & Specs
```

## Roadmap

-   **Cycle 02:** Interactive Engine & Backend Persistence (Refinement Logic).
-   **Cycle 03:** Basic GUI - The "Read" Experience (Panel UI).
-   **Cycle 04:** Interactive Refinement - The "Write" Experience.
-   **Cycle 05:** Polish, Traceability & Final Release.

## License

MIT License. See [LICENSE](LICENSE) for details.
