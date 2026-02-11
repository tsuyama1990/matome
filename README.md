# Matome 2.0: Knowledge Installation System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome 2.0** is not just a summarization tool; it is a **Knowledge Installation System**. By implementing "Semantic Zooming" based on the **DIKW (Data, Information, Knowledge, Wisdom)** hierarchy, it transforms massive documents into interactive, navigable knowledge trees. It enables users to instantly grasp the core philosophy (Wisdom), understand the underlying mechanisms (Knowledge), and execute actionable steps (Information), all while maintaining traceability to the original text (Data).

## Key Features

-   **Semantic Zooming Engine**: Automatically restructures text into a 4-layer abstraction hierarchy (Wisdom, Knowledge, Information, Data).
-   **Prompt Strategy Pattern**: Modular summarization strategies including:
    -   **Wisdom**: Distills text into profound aphorisms.
    -   **Knowledge**: Extracts mental models and frameworks.
    -   **Information**: Generates actionable checklists.
-   **Interactive Knowledge Canvas**: A GUI (built with Panel) that allows users to explore the knowledge tree using a "Pyramid Navigation" interface.
-   **Chat-Based Refinement**: Users can "talk" to any node in the tree to rewrite it (e.g., "Explain this for a 5-year-old"), updating the knowledge base in real-time.
-   **RAPTOR-Powered**: Built on the robust Recursive Abstractive Processing engine for handling long contexts.

## Architecture Overview

Matome uses a layered architecture separating the Interactive Engine from the Presentation Layer.

```mermaid
graph TD
    User[User] -->|Interacts| Canvas[Matome Canvas (GUI)]

    subgraph "Presentation Layer (MVVM)"
        Canvas -->|Binds| VM[InteractiveSession (ViewModel)]
        VM -->|Updates| Canvas
    end

    subgraph "Application Layer"
        VM -->|Calls| IRE[InteractiveRaptorEngine]
        IRE -->|Manages| SA[SummarizationAgent]
    end

    subgraph "Domain Logic"
        SA -->|Uses| PS[PromptStrategy (Wisdom/Knowledge/Info)]
    end

    subgraph "Data Layer"
        IRE -->|Reads/Writes| DCS[DiskChunkStore]
        DCS -->|Persists| DB[(SQLite: chunks.db)]
    end
```

## Prerequisites

-   **Python 3.11+**
-   **uv** (Recommended for dependency management)
-   **OpenRouter API Key** (or OpenAI API Key)

## Installation & Setup

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/matome.git
    cd matome
    ```

2.  **Install dependencies**
    Using `uv`:
    ```bash
    uv sync
    ```

3.  **Configure Environment**
    Create a `.env` file or set the environment variable:
    ```bash
    export OPENROUTER_API_KEY="your_key_here"
    ```

## Usage

### Batch Generation (CLI)
To generate a summarization tree from a text file:
```bash
uv run matome run input.txt
```
*(Note: DIKW mode flag `--mode dikw` will be enabled in Cycle 02)*

### Interactive Canvas (GUI)
To launch the interactive knowledge explorer:
```bash
uv run python -m matome.ui.launch
```
*(Note: Requires implementation of Cycle 04/05)*

## Development Workflow

This project follows a strict 5-cycle implementation plan.

1.  **Run Tests**:
    ```bash
    uv run pytest
    ```

2.  **Linting & Type Checking**:
    The project enforces strict code quality.
    ```bash
    uv run ruff check .
    uv run mypy .
    ```

## Project Structure

```
src/
├── domain_models/      # Pydantic Schemas (Config, NodeMetadata)
└── matome/
    ├── agents/         # SummarizationAgent, PromptStrategies
    ├── engines/        # RaptorEngine, InteractiveRaptorEngine
    ├── ui/             # Panel GUI (Canvas, Session)
    ├── utils/          # DiskChunkStore
    └── cli.py          # Command Line Interface
dev_documents/
├── system_prompts/     # Architecture & Cycle Specs
└── tutorials/          # Jupyter Notebooks
```

## License

MIT License
