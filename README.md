# Matome 2.0: Knowledge Installation System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Transform static documents into interactive Knowledge Trees.**
Matome 2.0 goes beyond simple summarization. It uses the **RAPTOR** algorithm and a novel **Semantic Zooming** engine to break down complex texts into a **DIKW (Data-Information-Knowledge-Wisdom)** hierarchy. Users can explore high-level philosophical insights ("Wisdom") and drill down into actionable checklists ("Information"), customizing the knowledge to fit their mental models.

## Key Features

*   **Semantic Zooming Engine:** Automatically generates distinct layers of abstraction:
    *   **Wisdom (Root):** Profound aphorisms and guiding principles.
    *   **Knowledge (Branches):** Structural explanations and mental models.
    *   **Information (Leaves):** Actionable steps and checklists.
    *   **Data (Source):** Original text chunks for verification.
*   **Interactive Matome Canvas:** A modern **Panel-based GUI** that allows you to explore the knowledge tree visually, expanding and collapsing branches as needed.
*   **Real-Time Refinement:** Don't like a summary? Chat with it! Instruct the system to "Make this simpler" or "Add more examples," and watch the tree update instantly.
*   **Hybrid Architecture:** Fully compatible with both automated batch processing (CLI) and interactive exploration (GUI), powered by a robust SQLite backend.

## Architecture Overview

Matome 2.0 is built on a layered architecture separating the Core Engine from the Presentation Layer.

```mermaid
graph TD
    subgraph "Presentation Layer"
        CLI[CLI (Typer)]
        GUI[GUI (Panel App)]
    end

    subgraph "Application Layer"
        IRE[InteractiveRaptorEngine]
        RE[RaptorEngine]
        SA[SummarizationAgent]
    end

    subgraph "Data Layer"
        Store[DiskChunkStore (SQLite)]
        Models[Domain Models (Pydantic)]
    end

    CLI --> RE
    GUI --> IRE
    IRE --> SA
    RE --> SA
    IRE --> Store
    RE --> Store
    Store --> Models
```

## Prerequisites

*   **Python 3.11+**
*   **uv** (Recommended for dependency management) or `pip`
*   **OpenAI API Key** (or OpenRouter) for LLM generation.

## Installation & Setup

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
    Copy the example environment file and add your API key.
    ```bash
    cp .env.example .env
    # Edit .env and set OPENAI_API_KEY=sk-...
    ```

## Usage

### 1. Batch Processing (CLI)
Generate the initial DIKW tree from a text file.

```bash
# Basic run
python -m matome.cli run path/to/your/document.txt

# Specify model
python -m matome.cli run document.txt --model openai/gpt-4o
```
This creates a `results/chunks.db` containing the knowledge tree.

### 2. Interactive Exploration (GUI)
Launch the Matome Canvas to explore and refine the generated tree.

```bash
# Launch the Panel server
python -m matome.ui.app results/chunks.db
```
Open your browser at `http://localhost:5006`.

## Development Workflow

We follow a 5-Cycle AC-CDD development process.

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

### Linting & Formatting
Strict code quality is enforced.
```bash
# Check code quality
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Type checking
mypy src
```

## Project Structure

```ascii
src/matome/
├── agents/         # LLM interaction & Prompt Strategies
├── engines/        # Core logic (RAPTOR, Interactive)
├── ui/             # Panel GUI components (MVVM)
├── utils/          # Database & Helper functions
└── cli.py          # Command Line Interface

src/domain_models/  # Pydantic schemas (Node, Metadata)
dev_documents/      # Architecture & Spec documentation
tests/              # Unit & Integration tests
```

## License

This project is licensed under the MIT License. See `LICENSE` for details.
