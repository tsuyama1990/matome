# Matome 2.0: "Knowledge Installation" System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome 2.0** is an interactive knowledge acquisition system designed to transform passive reading into active understanding. Unlike traditional summarization tools that compress text, Matome 2.0 restructures information into a **DIKW (Data, Information, Knowledge, Wisdom) hierarchy**, allowing users to "Semantic Zoom" from high-level philosophical insights down to actionable checklists and raw evidence.

It acts as a "Thought Partner," helping you install the mental models of complex texts directly into your brain.

## Key Features

-   **Semantic Zooming:** Traverse your document from L1 (Wisdom) -> L2 (Knowledge) -> L3 (Action) -> L4 (Data).
-   **DIKW Generation Engine:** Automatically categorizes summaries into Wisdom (Why), Knowledge (What), and Action (How).
-   **Interactive Refinement:** Don't like a summary? Chat with the node to refine it (e.g., "Make this simpler," "Translate to Japanese") without re-processing the whole document.
-   **Visual Knowledge Graph:** A Panel-based GUI that visualizes the logical structure of the text.
-   **Zero-Config Setup:** Works out of the box with OpenAI API.

## Architecture Overview

Matome 2.0 uses a layered architecture separating the Interactive GUI from the Core Logic.

```mermaid
graph TD
    User((User)) -->|Interacts| GUI[Panel GUI]
    GUI <-->|Binds| VM[InteractiveSession]
    VM -->|Calls| Engine[InteractiveRaptorEngine]

    subgraph "Core Logic"
        Engine -->|Uses| Agent[SummarizationAgent]
        Engine -->|Reads/Writes| Store[DiskChunkStore]
        Agent -->|Uses| Strategy[PromptStrategy]
        Strategy <|-- Wisdom[WisdomStrategy]
        Strategy <|-- Knowledge[KnowledgeStrategy]
        Strategy <|-- Action[ActionStrategy]
    end

    subgraph "Storage"
        Store -->|SQL| DB[(SQLite: chunks.db)]
    end
```

## Prerequisites

-   **Python 3.11+**
-   **OpenAI API Key** (for generation)
-   **uv** (recommended) or pip

## Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/matome.git
    cd matome
    ```

2.  **Install dependencies (using uv):**
    ```bash
    uv sync
    ```
    *Or using pip:*
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

### 1. GUI Mode (Recommended)
Launch the interactive application:
```bash
uv run matome gui
```
Open your browser to `http://localhost:5006/app`.

### 2. CLI Mode (Batch Processing)
Generate a DIKW tree from a text file:
```bash
uv run matome run path/to/document.txt --mode dikw
```
This will create a `results/chunks.db` file.

## Development Workflow

This project follows a cycle-based development plan.

**Running Tests:**
```bash
uv run pytest
```

**Linting & Type Checking:**
We enforce strict code quality.
```bash
uv run ruff check .
uv run mypy .
```

## Project Structure

```ascii
src/
├── domain_models/          # Pydantic Models (Shared Domain Kernel)
├── matome/
│   ├── agents/             # LLM Interaction Logic
│   ├── engines/            # RAPTOR & Interactive Engines
│   ├── strategies/         # Prompt Strategies (Wisdom, Knowledge, Action)
│   ├── gui/                # Panel Application (View & ViewModel)
│   └── utils/              # Database & Helper Utilities
dev_documents/
├── system_prompts/         # Cycle Specifications
└── ALL_SPEC.md             # Original Requirements
tests/                      # Unit & Integration Tests
```

## License

This project is licensed under the MIT License.
