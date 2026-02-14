# Matome 2.0: Knowledge Installation System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome 2.0** is an interactive "Knowledge Installation" system that transforms long-form text into a structured DIKW (Data, Information, Knowledge, Wisdom) hierarchy. Unlike static summarizers, it allows you to explore information at varying levels of abstraction—from philosophical wisdom down to actionable checklists—and interactively refine the content to match your mental model.

## Key Features

-   **Semantic Zooming (DIKW Pyramid):** Navigate your documents like a map. Zoom out for "Wisdom" (The Big Idea) and zoom in for "Information" (Actionable Steps).
-   **Interactive Refinement:** Don't like a summary? Tell the AI to "rewrite it for a 5-year-old" or "focus on the financial risks," and watch it update in real-time.
-   **Traceability:** Every piece of wisdom is linked back to the original text chunks ("Data"), ensuring you can always verify the source of an insight.
-   **Local First:** Powered by `SQLite` and `Panel`, your knowledge base runs locally on your machine, ensuring privacy and speed.

## Architecture Overview

Matome 2.0 uses a **Reverse-DIKW** logic built on top of the RAPTOR recursive summarization engine.

```mermaid
graph TD
    User[User] -->|Interacts| GUI[Matome Canvas (Panel)]

    subgraph Presentation Layer
        GUI -->|View State| VM[InteractiveSession]
        GUI -->|Refine Request| Controller[InteractiveRaptorEngine]
    end

    subgraph Application Layer
        Controller -->|Get Nodes| Store[DiskChunkStore]
        Controller -->|Summarize/Refine| Agent[SummarizationAgent]
    end

    subgraph Domain Layer
        Agent -->|Uses| Strategy[PromptStrategy]
        Strategy <|-- WisdomStrat[Wisdom]
        Strategy <|-- KnowledgeStrat[Knowledge]
        Strategy <|-- InfoStrat[Information]
    end

    subgraph Infrastructure Layer
        Store -->|Read/Write| DB[(SQLite / chunks.db)]
        Agent -->|API Call| LLM[OpenAI API]
    end
```

## Prerequisites

-   **Python 3.11+**
-   **uv** (Recommended package manager)
-   **OpenAI API Key** (Set in `.env` as `OPENAI_API_KEY`)

## Installation & Setup

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
    ```bash
    cp .env.example .env
    # Edit .env and add your OPENAI_API_KEY
    ```

## Usage

### Quick Start: Generate & Explore

1.  **Ingest a Document:**
    Run the CLI to generate the initial DIKW tree from a text file.
    ```bash
    uv run matome run path/to/document.txt --mode dikw
    ```

2.  **Launch the Canvas:**
    Start the interactive GUI to explore and refine the knowledge.
    ```bash
    uv run matome serve results/chunks.db
    ```

3.  **Access the UI:**
    Open your browser at `http://localhost:5006/matome`.

## Development Workflow

We follow a rigorous development process divided into 5 cycles.

**Running Tests:**
```bash
uv run pytest
```

**Linting & Type Checking:**
We enforce strict quality standards using `ruff` and `mypy`.
```bash
uv run ruff check .
uv run mypy .
```

**Running UAT Tutorials:**
We use `marimo` for interactive verification.
```bash
uv run marimo edit tutorials/UAT_AND_TUTORIAL.py
```

## Project Structure

```
matome/
├── src/
│   ├── domain_models/  # Pydantic schemas (SummaryNode, Chunk)
│   ├── matome/
│   │   ├── agents/     # LLM Logic & PromptStrategies
│   │   ├── engines/    # RAPTOR & Interactive Engines
│   │   ├── ui/         # Panel GUI (Canvas, ViewModel)
│   │   └── utils/      # DB Storage & Helpers
├── tests/              # Pytest suite
├── dev_documents/      # Architecture specs & Design docs
└── tutorials/          # Marimo UAT notebooks
```

## License

MIT License. See [LICENSE](LICENSE) for details.
