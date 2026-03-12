# matome (まとめ)

## Overview
matome is an interactive summarization and knowledge extraction tool specifically designed for very long texts. It leverages cognitive psychology principles alongside cutting-edge generative AI to mitigate cognitive overload. By converting large documents into structured RAPTOR graphs, matome ensures frictionless active learning and insight generation.

## Features
- **Semantic Structuring:** Break documents down into meaningful semantic chunks and structured data using predefined multi-level models.
- **Pydantic Validation:** Strict enforcement of domain types, ensuring no malformed outputs pass through the system.
- **Encryption:** Enterprise-grade encryption of sensitive API Keys via `cryptography.fernet`.
- **FastAPI Foundation:** Setup with FastAPI, ready to deploy API endpoints with high performance.

## Installation

Ensure you have [uv](https://github.com/astral-sh/uv) installed, then run the following:

```bash
uv sync
```

## Usage

To start the API service, simply run:

```bash
uv run python src/main.py
```

Check the health of the application by navigating to `http://localhost:8000/health`.

## Structure

```text
.
├── src/
│   ├── main.py                  # FastAPI application entry point
│   ├── di_container.py          # Dependency Injection Container
│   ├── domain_models/           # Core Pydantic schemas (Strictly typed, zero dependencies)
│   │   ├── config.py            # System configuration and Cryptographic models
│   │   ├── document.py          # Document, Chunk, and Node models
│   │   └── exceptions.py        # Domain exceptions
│   └── infrastructure/          # External adapters
│       └── interfaces.py        # Abstract interfaces for infrastructure
├── tests/                       # Comprehensive test suite (Unit)
├── dev_documents/               # System architecture and user acceptance criteria
├── pyproject.toml               # Project metadata and strict linter rules
└── README.md                    # Landing page and setup instructions
```
