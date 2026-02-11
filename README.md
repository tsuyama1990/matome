# Matome 2.0: Knowledge Installation System

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**Matome 2.0** is not just a summarization tool; it is a **Cognitive Augmentation System**. It transforms long, complex documents into a structured **DIKW (Data, Information, Knowledge, Wisdom)** hierarchy, allowing users to "install" knowledge into their minds through **Semantic Zooming** and **Interactive Refinement**.

Instead of reading a static summary, you interact with a living knowledge tree—starting from a single profound "Wisdom" aphorism and zooming all the way down to the raw "Data" evidence, refining the mental model as you go.

## Key Features

-   **Semantic Zooming**: Traverse the abstraction ladder effortlessly. Click a philosophical "Wisdom" node to reveal the structural "Knowledge" behind it, and drill down further to actionable "Information" checklists.
-   **DIKW Generation Engine**: Uses advanced Prompt Strategy Patterns to strictly categorize content. It doesn't just "summarize"; it extracts "Mechanisms" for Knowledge and "Checklists" for Action.
-   **Interactive Refinement**: Don't like an explanation? Rewrite it! The "Human-in-the-Loop" chat interface allows you to critique and refine specific nodes, creating a personalized knowledge base.
-   **Source Traceability**: Never blindly trust the AI. Every leaf node links directly back to the original text chunks for verification.
-   **Local-First Architecture**: Powered by SQLite and Panel, running entirely in your local environment (with LLM API calls).

## Architecture Overview

Matome 2.0 decouples the Generation Engine from the Interactive Interface, bridging them with a robust Controller.

```mermaid
graph TD
    User[User] -->|Interacts| GUI[Panel GUI (View)]
    GUI <-->|Binds| VM[InteractiveSession (ViewModel)]
    VM -->|Calls| Controller[InteractiveRaptorEngine]

    subgraph "Core Engine"
        Controller -->|Uses| Store[DiskChunkStore (SQLite)]
        Controller -->|Uses| Agent[SummarizationAgent]
        Agent -->|Uses| Strategy[PromptStrategy Interface]

        Strategy <|-- W[WisdomStrategy]
        Strategy <|-- K[KnowledgeStrategy]
        Strategy <|-- A[ActionStrategy]
    end

    subgraph "External"
        LLM[OpenAI / LLM API]
    end

    Agent -->|API Call| LLM
```

## Prerequisites

-   **Python 3.11+**
-   **uv** (Recommended for dependency management) or `pip`.
-   **OpenAI API Key** (or compatible LLM provider).

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
    pip install -e ".[dev]"
    ```

3.  **Configure Environment**
    Copy the example environment file and add your API key.
    ```bash
    cp .env.example .env
    # Edit .env and set OPENAI_API_KEY=sk-...
    ```

## Usage

### 1. Generate a Knowledge Tree
Process a raw text file into a DIKW database.
```bash
# Using the new DIKW mode
uv run matome run data/my_book.txt --mode dikw
```

### 2. Launch the Canvas
Open the interactive GUI to explore and refine the knowledge.
```bash
uv run matome canvas results/chunks.db
```
This will start a local server (typically at `http://localhost:5006`).

## Development Workflow

This project follows a strict cycle-based development process.

**Running Tests**:
```bash
uv run pytest
```

**Linting & Formatting**:
We enforce strict code quality using `ruff` and `mypy`.
```bash
uv run ruff check .
uv run mypy .
```

**Project Structure**:
```
src/matome/
├── agents/         # LLM interaction & Strategies
├── engines/        # RAPTOR & Interactive Controllers
├── interface/      # Panel GUI (MVVM)
├── utils/          # Database & Helpers
└── cli.py          # Command Line Interface

src/domain_models/  # Pydantic Schemas (Manifest, Metadata)
dev_documents/      # Architecture & Specs
```

## License

This project is licensed under the MIT License.
