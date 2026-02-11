# Matome 2.0: Knowledge Installation Platform

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome 2.0** solves the "Information Overload" problem by transforming massive documents into navigable, interactive knowledge trees. Unlike traditional summarizers that simply compress text, Matome uses **Semantic Zooming** to organize content into a **DIKW (Data, Information, Knowledge, Wisdom)** hierarchy, allowing you to instantly grasp the "Why" (Wisdom) before drilling down into the "How" (Actionable Information).

## Key Features

*   **Semantic Zooming**: Navigate smoothly between abstraction levels:
    *   **Wisdom (L1)**: Profound aphorisms and core truths.
    *   **Knowledge (L2)**: Mental models and structural explanations.
    *   **Information (L3)**: Actionable checklists and steps.
    *   **Data (L4)**: Original source text.
*   **Interactive Refinement**: Don't like a summary? Rewrite it. The built-in GUI allows you to refine specific nodes using natural language instructions (e.g., "Make this simpler", "Translate to Japanese").
*   **Matome Canvas (GUI)**: A modern, reactive web interface built with **Panel** for exploring and editing your knowledge base.
*   **Type-Safe Architecture**: Built with **Pydantic** and **Python 3.11+** for robustness and maintainability.

## Architecture Overview

Matome 2.0 separates the *Interface* (CLI/GUI) from the *Application Logic* (Engines/Agents), using a Strategy Pattern to handle different abstraction levels.

```mermaid
graph TD
    subgraph Interface Layer
        CLI[CLI (Typer)]
        GUI[Matome Canvas (Panel)]
    end

    subgraph Application Layer
        RE[RaptorEngine]
        IRE[InteractiveRaptorEngine]
        SA[SummarizationAgent]

        CLI --> RE
        GUI --> IRE
        RE --> SA
        IRE --> SA
    end

    subgraph Infrastructure Layer
        DSC[DiskChunkStore (SQLite)]
        RE --> DSC
        IRE --> DSC
    end
```

## Prerequisites

*   **Python 3.11+**
*   **uv** (Fast Python package manager)
*   **OpenRouter API Key** (or OpenAI API Key)

## Installation & Setup

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/matome.git
    cd matome
    ```

2.  **Install dependencies**
    ```bash
    uv sync
    ```

3.  **Configure Environment**
    Create a `.env` file and add your API key:
    ```bash
    export OPENROUTER_API_KEY="sk-or-..."
    ```

## Usage

### 1. Batch Processing (CLI)
Generate the initial knowledge tree from a text file.

```bash
uv run matome run input.txt --mode dikw
```

### 2. Interactive Exploration (GUI)
Launch the Matome Canvas to explore and refine the generated knowledge.

```bash
uv run matome ui chunks.db
```

## Development Workflow

This project follows a cycle-based development process.

*   **Run Tests**:
    ```bash
    uv run pytest
    ```
*   **Lint & Format**:
    ```bash
    uv run ruff check .
    uv run ruff format .
    ```
*   **Type Check**:
    ```bash
    uv run mypy .
    ```

## Project Structure

```ascii
src/matome/
├── agents/         # Summarization and Verification Agents
├── engines/        # RAPTOR and Interactive Engines
├── ui/             # Panel GUI (View & ViewModel)
├── utils/          # Storage and Helpers
└── cli.py          # Entry point
```

## License

MIT License
