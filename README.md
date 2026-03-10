# matome

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)

## Overview

**matome** ("summary" in Japanese) is an advanced active learning and document analysis platform designed to liberate users from the pain of digesting massive amounts of information. By seamlessly integrating cognitive psychology principles (such as the SQ3R method and Semantic Zooming) with the latest generative AI technologies (including RAPTOR, GraphRAG, and Multi-Dimensional Semantic KJ), it transforms knowledge acquisition and insight generation into an exhilarating, frictionless intellectual game.

## Features

- **Progressive Disclosure & Semantic Zooming:** Mitigates cognitive overload by presenting an initial high-level mind map (RAPTOR tree). As you focus, the resolution dynamically increases to reveal details without overwhelming your working memory.
- **Frictionless SQ3R Automation:** Enforces active learning by requiring you to interactively answer context-aware, AI-generated questions before unlocking deeper semantic nodes, supported by satisfying micro-gamification rewards.
- **Pivot KJ (Multi-Dimensional Knowledge Restructuring):** Easily dismantle the author's original structure and reorganise information along new axes (e.g., SWOT, System Design workflows) to effortlessly generate completely new insights.
- **Automated Workflow Export:** Quickly convert legacy business manuals into modern, AI-validated Requirements Documents and Mermaid.js UML diagrams (sequence diagrams, flowcharts, ER diagrams).
- **Secure & Configurable AI Routing:** Enterprise-ready architecture featuring strict environment variable-driven configurations, enabling Bring Your Own Key (BYOK) with guaranteed zero-data retention constraints.

## Requirements

- **Python:** 3.12 or higher
- **Package Manager:** [uv](https://github.com/astral-sh/uv)
- **API Keys:** An active [OpenRouter](https://openrouter.ai/) API Key

## Installation

1. Clone the repository to your local machine:
   ```bash
   git clone https://github.com/yourusername/matome.git
   cd matome
   ```

2. Install dependencies rapidly using `uv`:
   ```bash
   uv sync
   ```

3. Configure your environment variables. Copy the `.env.example` file and configure your credentials and application settings:
   ```bash
   cp .env.example .env
   # Ensure you set OPENROUTER_API_KEY=your_key_here
   ```

## Usage

Start the main matome backend server:

```bash
uv run python main.py server
```

*Note: The API server will be exposed locally at `http://127.0.0.1:8000`.*

### User Acceptance Testing (UAT)

To experience the foundational UAT simulation script directly:

```bash
PYTHONPATH=. uv run python tests/uat/uat_script.py
```

## Architecture

The matome platform is constructed upon a highly modern, event-driven modular monolith architecture:
- **Strict Configuration Schema:** Relies completely on Pydantic `BaseSettings` for rigid enforcement of configuration structures and secrets encapsulation.
- **Dependency Injection Container:** Decouples core business domains from infrastructure dependencies via explicitly defined Protocols.
- **Data Domains:** Implements strict data constraints enforcing the separation between structural identities (`IdentityNode`) and raw unstructured text content (`ContentNode`).

## Roadmap

Development is meticulously staged into iterative cycles, ensuring maximum stability as capabilities progressively expand:
- **Core Infrastructure Foundation:** Establishing Pydantic constraints and dependency pipelines (Currently completed).
- **Resilient Ingestion:** Integration of massive file processing and semantic chunking.
- **RAPTOR Construction:** Graph generation and self-correcting summarization pipelines.
- **Semantic Zooming:** Exposing interactive API endpoints for UI-driven workflows.
- **Pivot KJ:** Mathematical spatial transformation and Web-Grounding integration.
- **Enterprise Security:** Hardening paths, zeroizing credentials in memory, and final performance tuning.

## License

This project is licensed under the MIT License.
