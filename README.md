# Matome 2.0: Knowledge Installation System

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**Matome 2.0** is a **Cognitive Augmentation System**. It transforms long, complex documents into a structured **DIKW (Data, Information, Knowledge, Wisdom)** hierarchy.

*Note: This version (Cycle 01) implements the foundational DIKW data structures and Strategy Pattern architecture. Semantic Zooming and Interactive GUI are in active development.*

## Features

-   **DIKW Metadata Schema**: Nodes are now tagged with their abstraction level (Wisdom, Knowledge, Information, Data).
-   **Prompt Strategy Pattern**: Flexible architecture allowing different summarization styles for each level.
-   **Robust Validation**: Strict Pydantic models ensure data integrity and schema compliance.
-   **Backward Compatibility**: Automatically upgrades legacy databases to the new schema without data loss.

## Requirements

-   **Python 3.11+**
-   **uv** (Recommended) or `pip`.

## Installation

```bash
git clone https://github.com/yourusername/matome.git
cd matome
uv sync
```

## Usage

Process a text file using the RAPTOR engine (currently using Base Strategy):
```bash
uv run matome run path/to/document.txt
```

Run tests to verify the installation:
```bash
uv run pytest
```

## Architecture

```
src/matome/
├── agents/         # SummarizationAgent & Strategies
├── engines/        # RAPTOR Engine
├── utils/          # Database & Helpers
└── cli.py          # Command Line Interface

src/domain_models/  # Pydantic Schemas (Manifest, Metadata, Config)
```

## License

This project is licensed under the MIT License.
