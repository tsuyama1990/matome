# Matome 2.0: Knowledge Installation System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome 2.0** is an interactive knowledge acquisition platform designed to solve information overload. Unlike traditional summarizers that simply shorten text, Matome 2.0 employs **Semantic Zooming** based on the DIKW (Data, Information, Knowledge, Wisdom) hierarchy. It transforms massive documents into a navigable "Google Earth" of knowledge, allowing users to zoom from high-level philosophy down to actionable checklists, and interactively refine the content to suit their mental models.

## Key Features

*   **Semantic Zooming (DIKW Engine)**:
    *   **Wisdom (L1)**: Distills core philosophy and aphorisms (The "Why").
    *   **Knowledge (L2)**: Explains structural frameworks and mechanisms (The "How").
    *   **Information (L3)**: Generates actionable checklists and instructions (The "What").
*   **Matome Canvas (Interactive UI)**: A modern web interface (built with Panel) for exploring the knowledge pyramid and visualizing connections.
*   **Interactive Refinement**: "Talk to your data." Rewrite any part of the summary tree using natural language instructions (e.g., "Explain this for a 5-year-old").
*   **Source Verification**: Instantly trace any abstract insight back to the original raw text chunks to prevent hallucinations.
*   **Recursive Summarization (RAPTOR)**: Uses advanced recursive clustering to ensure no context is lost, even in books of 500+ pages.

## Architecture Overview

Matome 2.0 is built on a modular architecture separating the generation engine from the interactive session management.

```mermaid
graph TD
    User[User] --> GUI[Matome Canvas (Panel)]
    GUI --> Session[Interactive Session (ViewModel)]
    Session --> IRE[Interactive Raptor Engine]
    IRE --> Store[DiskChunkStore (SQLite)]
    IRE --> Agent[Summarization Agent]
    Agent --> Strategy[Prompt Strategies (Wisdom/Knowledge/Action)]
    Agent --> LLM[LLM (OpenAI/Anthropic)]
    Store --> Models[Data Models]
```

## Prerequisites

*   **Python 3.11+**
*   **uv** (Recommended) or pip.
*   **OpenRouter API Key** (or OpenAI/Anthropic key) for LLM access.

## Installation & Setup

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
    Copy the example environment file and set your API key:
    ```bash
    cp .env.example .env
    # Edit .env and set OPENROUTER_API_KEY
    ```

## Usage

### 1. Batch Processing (CLI)
Generate the initial knowledge tree from a text file.

```bash
# Standard summarization
uv run matome run input.txt

# DIKW Semantic Zooming mode
uv run matome run input.txt --mode dikw
```

### 2. Interactive Exploration (GUI)
Launch the Matome Canvas to explore and refine the results.

```bash
uv run python -m matome.ui.app
```
*   Open your browser at `http://localhost:5006`.
*   Navigate the tree on the left sidebar.
*   Click "Refine" to rewrite nodes.

## Development Workflow

We follow a strict 5-cycle development plan.

1.  **Run Tests**:
    ```bash
    uv run pytest
    ```
2.  **Linting & Formatting**:
    ```bash
    uv run ruff check .
    uv run ruff format .
    ```
3.  **Type Checking**:
    ```bash
    uv run mypy .
    ```

## Project Structure

```text
src/
├── domain_models/      # Pydantic models (SummaryNode, NodeMetadata)
├── matome/
│   ├── agents/         # AI Logic (Summarizer, Verifier, Strategies)
│   ├── engines/        # Processing (Raptor, Interactive, Chunker)
│   ├── ui/             # Panel GUI (App, ViewModel, Components)
│   └── utils/          # DB & IO
└── tests/              # Unit and Integration tests
```

## License

MIT License. See `LICENSE` for details.
