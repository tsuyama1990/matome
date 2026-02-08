# Matome: Long Context Summarization System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Matome** is a next-generation document processing platform that solves the "Lost-in-the-Middle" problem in Large Language Models. By combining **Recursive Abstractive Processing (RAPTOR)** with **Japanese-optimized Semantic Chunking** and **GraphRAG** concepts, it transforms massive documents into structured, navigable, and verifiable knowledge trees.

## Key Features

*   **Recursive Summarization (RAPTOR)**: Builds a hierarchical tree of summaries, capturing both the high-level narrative and granular details without losing context.
*   **Japanese-Optimized Chunking**: Uses specialized regex patterns to split text at natural semantic boundaries (punctuation, quotes) rather than arbitrary character limits.
*   **Cost-Effective Architecture**: Intelligently routes tasks to the most efficient model (Gemini 1.5 Flash for bulk work, DeepSeek/GPT-4 for reasoning), reducing costs by up to 90%.
*   **Visual Knowledge Maps**: Exports results to **Obsidian Canvas**, allowing users to interactively explore and rearrange the generated knowledge structure (KJ Method).
*   **Hallucination Verification**: Implements Chain-of-Verification (CoVe) to cross-check summaries against source text, ensuring high factual accuracy.

## Architecture Overview

Matome uses a pipeline approach to ingest, process, and synthesize information.

```mermaid
graph TD
    User[User Input] -->|PDF/TXT| Ingest[Ingestion Layer]
    Ingest -->|Clean Text| Chunk[Chunking Engine]
    Chunk -->|Semantic Chunks| Embed[Embedding Service]
    Embed -->|Vectors| Cluster[Clustering (UMAP/GMM)]
    Cluster -->|Cluster Indices| Summarizer[Summarization Agent (CoD)]
    Summarizer -->|Cluster Summaries| Recursion{Is Root?}
    Recursion -- No --> Embed
    Recursion -- Yes --> Verify[Verification Module]
    Verify -->|Verified Tree| Format[Presentation Layer]
    Format -->|Markdown| Out1[summary_all.md]
    Format -->|Obsidian Canvas| Out2[summary_kj.md]
```

## Prerequisites

*   **Python 3.11+**
*   **API Key**: An [OpenRouter](https://openrouter.ai/) API key is required for the summarization engine.
*   **UV** (Recommended for dependency management) or pip.

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
    Create a `.env` file in the root directory:
    ```bash
    export OPENROUTER_API_KEY="sk-or-your-api-key-here"
    ```

## Usage

### Quick Start (CLI)

To process a document and generate both a markdown summary and an Obsidian Canvas map:

```bash
# Run the full pipeline
python -m matome.cli run input_document.txt --output-dir results/

# Expected Output:
# results/summary_all.md
# results/summary_kj.canvas
```

### Mock Mode (No API Cost)

For testing or development without spending credits, verify the pipeline flow using mock mode:

```bash
export OPENROUTER_API_KEY="mock"
python -m matome.cli run test_data/sample.txt
```

## Development Workflow

We follow a strict development cycle with rigorous linting and testing.

### Running Tests
```bash
pytest
```

### Linting & Formatting
This project uses `ruff` and `mypy` (strict mode).

```bash
ruff check .
mypy .
```

### Implementation Cycles
The project is divided into 6 cycles. See `dev_documents/system_prompts/CYCLE{xx}/SPEC.md` for details on each phase.
1.  **Foundation**: Text ingestion and chunking.
2.  **Clustering**: Embedding and GMM logic.
3.  **Summarization**: LLM integration.
4.  **RAPTOR**: Recursive tree building.
5.  **Visualization**: Obsidian Canvas export.
6.  **Verification**: Hallucination checks and CLI polish.

## Project Structure

```
.
├── dev_documents/          # Specs and UAT plans
├── src/
│   └── matome/             # Source code
│       ├── agents/         # LLM interaction logic
│       ├── domain/         # Pydantic data models
│       ├── engines/        # Core algorithms (Chunker, Cluster, Raptor)
│       └── exporters/      # Output generators
├── tests/                  # Unit tests
└── pyproject.toml          # Configuration
```

## License

MIT License. See [LICENSE](LICENSE) for details.
