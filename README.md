# matome

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)

"To liberate humanity from the pain of digesting information, transforming knowledge acquisition into an exhilarating intellectual game."

## Overview
**matome** (Japanese for "summary") is an advanced interactive knowledge workspace designed to revolutionize how professionals digest massive amounts of text. By seamlessly integrating the latest generative AI, cognitive psychology principles (SQ3R), and high-performance visual interfaces, it transforms static reading into an active learning and knowledge-restructuring experience. It's built for Product Managers, Consultants, Researchers, and Students to conquer information overload.

## Features
*   **Frictionless Active Learning (SQ3R Automation):** The system automatically locks content and prompts you with questions before reading, ensuring active engagement and drastically improving long-term memory retention.
*   **Semantic Zoom Interface:** Utilises a progressive disclosure UI to prevent cognitive overload. Start with a high-level mind map and zoom smoothly into dense, AI-refined summaries as needed.
*   **Multi-Dimensional Pivot KJ Analysis:** Dynamically restructure your documents. Instantly transform a rigid, chapter-based legacy manual into an agile, actor-vs-state workflow diagram with a single click.
*   **AI Metadata Tracking:** Preserves semantic contexts, entity recognition metadata, and GMM hierarchical trees for advanced NLP processing and graph structuring.
*   **Enterprise-Grade Privacy & BYOK:** Designed with security first. Utilize local inference options or Bring Your Own Key (BYOK) for OpenRouter to ensure your sensitive data is never used for external AI training.
*   **Strict Typing and Validation:** Provides robust validation using precise, type-safe Domain Schemas (Pydantic Models).

## Requirements
*   Python 3.12+
*   `uv` package manager
*   OpenRouter API Key (optional for Mock Mode)

## Installation
```bash
# Clone the repository
git clone https://github.com/your-org/matome.git
cd matome

# Install dependencies using uv
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY if applicable
```

## Usage
Run the interactive User Acceptance Test (UAT) and tutorial using marimo:
```bash
uv run marimo edit tutorials/UAT_AND_TUTORIAL.py
```

Example basic python script usage:
```python
from src.domain_models import DocumentNode, NodeStatus

# Initialize a node representing a semantic chunk
node = DocumentNode(
    id="node-123",
    title="Chapter 1: The Basics",
    status=NodeStatus.UNLOCKED,
    metadata={"Time Axis": "Present"}
)

print(node.model_dump_json(indent=2))
```

## Architecture/Structure
The matome platform employs a modern, decoupled architecture designed for high performance and extensibility.
It uses a React/React Flow frontend to deliver 60fps interactive canvases and a FastAPI Python backend orchestrated by LangGraph. It relies on a Vector Database for semantic chunking and retrieval, and utilizes OpenRouter to dynamically route AI tasks to the most cost-effective models.

```text
matome/
├── src/
│   ├── domain_models/   # Core Business Logic and strict Data Schemas
│   ├── interfaces/      # Interfaces (Repositories/Services Protocols)
│   └── ...
├── tests/
│   ├── unit/            # Unit tests for schemas and simple components
│   ├── e2e/             # End to End tests simulating user flows
│   └── uat/             # User Acceptance Test scripts/notebooks
├── tutorials/           # Interactive notebooks (Marimo) for users
├── dev_documents/       # Architectural planning and specifications
└── pyproject.toml       # Environment, Dependency Management, Linter Config
```

## Roadmap
*   Integration with Vector Databases (Pinecone/Qdrant)
*   React Flow Frontend UI rendering
*   Comprehensive LangGraph workflow logic
*   Automated REST API scaffolding using FastAPI

## License
MIT License
