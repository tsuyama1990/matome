# matome

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

## Overview

**matome** ("summary" in Japanese) is a revolutionary active learning and knowledge extraction platform. It liberates professionals from the intense cognitive load of deciphering massive, unstructured documents. By integrating advanced generative AI (like RAPTOR and Multi-Dimensional Semantic KJ) with proven cognitive psychology principles (SQ3R, spacing effects), matome transforms tedious reading into an exhilarating, gamified intellectual pursuit.

Whether you are a Product Manager deconstructing legacy manuals into modern workflows, or a consultant synthesizing numerous market reports into a novel strategy matrix, matome provides the "Aha!" moment instantly.

## Features

1.  **Frictionless Active Learning (SQ3R Automation)**: The system visually structures documents into a progressive hierarchical tree. To read details, users must interact by answering AI-generated reasoning prompts. Correct answers provide immediate visual rewards and highly dense summaries, ensuring deep long-term retention.
2.  **Semantic Zooming UI**: Drown no more in walls of text. matome starts with a high-level mind map. As you zoom in, resolution increases specifically for your area of interest (Progressive Disclosure) while maintaining your global context via minimaps and breadcrumbs.
3.  **Pivot KJ (Multi-Dimensional Knowledge Restructuring)**: Break the "As-Is trap" and author biases. Dismantle existing narrative flows and instantly automatically rearrange information across entirely new analytical dimensions (e.g., SWOT, System Workflows, Time Axes) to generate fresh insights and actionable system requirements.
4.  **Automated Diagram Generation**: Transform unstructured text into structured, standard formats immediately. Export restructured knowledge clusters directly into valid Markdown Product Requirements Documents (PRDs) and interactive Mermaid.js architecture diagrams (Sequence, Flowcharts, State Machines).
5.  **Multi-Modal Ingestion & AI Routing**: Process PDFs, EPUBs, and raw text seamlessly. The backend securely chunks data using semantic boundaries and dynamically routes queries to the optimal Large Language Model (LLM) via an OpenRouter gateway (`OpenRouterGateway`), balancing speed and reasoning capabilities.
6.  **Extensible Vector Search Architecture**: Integrated `VectorDBProtocol` ensures flexible and test-driven retrieval (including a mock database `MockVectorDB` for local and UI demonstrations).

## Requirements

To run this project, ensure you have the following installed on your system:

*   Python 3.12 or higher
*   `uv` (The extremely fast Python package and project manager)
*   A valid OpenRouter API Key (Optional for Mock Mode)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/matome.git
    cd matome
    ```

2.  **Initialize the environment and sync dependencies using `uv`:**
    ```bash
    uv sync
    ```

3.  **Configure environment variables:**
    Copy the example environment file and insert your API keys.
    ```bash
    cp .env.example .env
    # Edit .env and add OPENROUTER_API_KEY="your_api_key_here"
    ```

## Usage

### Quick Start with Interactive Tutorial

The best way to experience matome's capabilities and verify the User Acceptance Tests (UAT) is through our interactive Marimo notebook.

1.  Run the notebook using `uv`:
    ```bash
    PYTHONPATH=. uv run marimo edit tutorials/UAT_AND_TUTORIAL.py
    ```
2.  Follow the interactive steps within the notebook to simulate uploading a document, viewing the RAPTOR tree, interacting with the active learning prompts, and executing a Pivot KJ analysis to generate a Mermaid diagram.

### Starting the API Server

To start the FastAPI server for production or frontend integration:

```bash
PYTHONPATH=. uv run uvicorn src.main:app --reload
```

## Architecture

matome strictly adheres to Domain-Driven Design principles, ensuring maximum security, testability, and separation of concerns via a robust Dependency Injection container.

```mermaid
graph TD
    subgraph Presentation Layer
        UI[Frontend User Interface]
        API[FastAPI Endpoints]
        Marimo[Marimo Tutorial Notebook]
    end

    subgraph Application Service Layer
        DPS[Document Processing Service]
        KGS[Knowledge Graph Service]
        ALS[Active Learning Service]
        DI[Production DI Container]
    end

    subgraph Core Domain Layer
        Entities[Pydantic Domain Models]
        Constants[System Constants & Enums]
        Config[Pipeline Config & Credentials]
        Interfaces[Protocols / Interfaces]
    end

    subgraph Infrastructure Layer
        VDB[(Vector Database)]
        LLM_GW[OpenRouter Model Gateway]
        Storage[Local / S3 Storage]
        Auth[Security & RBAC]
    end

    UI --> API
    Marimo --> API
    API --> DPS
    API --> KGS
    API --> ALS

    DPS --> Interfaces
    KGS --> Interfaces
    ALS --> Interfaces

    Interfaces <.. VDB : Implements
    Interfaces <.. LLM_GW : Implements
    Interfaces <.. Storage : Implements
    Interfaces <.. Auth : Implements

    DPS -.-> Entities
    KGS -.-> Entities
    ALS -.-> Entities

    DI --> API : Injects Dependencies
```

## Roadmap

Future developments will focus on:
*   Integration with Local inference for highly secure on-premise deployments.
*   More expansive frontend customizations for complex diagram generations.
*   Further expansion of supported multimodal inputs (Video analysis).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
