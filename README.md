# Matome 2.0: Knowledge Installation System

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

**Turn static text into interactive knowledge graphs.**

Matome 2.0 is a **"Semantic Zooming" engine**. It breaks down long documents (books, reports) into a hierarchical structure, allowing you to traverse from high-level insights down to original source evidence.

## Features

- **Semantic Zooming (DIKW):** Generate summaries at different abstraction levels:
  - **Wisdom (L1):** Profound, concise aphorisms.
  - **Knowledge (L2):** Structural mental models and frameworks.
  - **Information (L3):** Actionable checklists and procedures.
  - **Data (L4):** Original text chunks.
- **Hierarchical Summarization (RAPTOR):** Recursively summarizes text to build a tree of knowledge.
- **Japanese Semantic Chunking:** Intelligent text splitting optimized for Japanese content.
- **Obsidian Canvas Export:** Visualize your summary as an interactive node graph in Obsidian.
- **Interactive Refinement:** Refine individual nodes using natural language instructions.

## Requirements

- **Python 3.11+**
- **uv** (Recommended package manager)
- **OpenRouter API Key** (Set as `OPENROUTER_API_KEY` environment variable)

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

## Usage

### Basic Command
Run the summarization pipeline on a text file:

```bash
uv run matome run data/sample.txt
```

### DIKW Modes
Select a specific mode to tailor the output:

```bash
# Generate profound insights (Wisdom)
uv run matome run data/sample.txt --mode wisdom

# Extract structural frameworks (Knowledge)
uv run matome run data/sample.txt --mode knowledge

# Create actionable checklists (Information)
uv run matome run data/sample.txt --mode information
```

### Options
- `--mode`: Summarization mode: `wisdom`, `knowledge`, `information`, `data` (default).
- `--output-dir`, `-o`: Directory to save results (default: `results`).
- `--model`, `-m`: Summarization model (default: `openai/gpt-4o-mini`).
- `--verify/--no-verify`: Enable/Disable verification (default: Enabled).

### Output
The command generates:
- `summary_all.md`: A full markdown summary.
- `summary_kj.canvas`: An Obsidian Canvas file for visualization.
- `chunks.db`: A SQLite database containing all nodes and embeddings.

## Architecture

```ascii
src/
├── domain_models/       # Pydantic schemas and configuration
├── matome/
│   ├── agents/          # LLM interaction & Strategies
│   │   ├── summarizer.py
│   │   └── strategies.py
│   ├── engines/         # RAPTOR & Clustering Logic
│   └── cli.py           # CLI Entry point
```

## Roadmap

- **Cycle 01:** Core Refactoring & Strategy Pattern.
- **Cycle 02:** DIKW Engine (Wisdom/Knowledge/Information modes).
- **Cycle 03 (Current):** Interactive Backend (Single-node refinement).
- **Cycle 04:** GUI Foundation (MVVM with Panel).
- **Cycle 05:** Full Semantic Zooming.

## License

MIT License.
