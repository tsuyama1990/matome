# matome

"To liberate humanity from the pain of digesting information, transforming knowledge acquisition and the creation of new insights into an exhilarating intellectual game."

## Overview
`matome` (Japanese for "summary") is an interactive knowledge workspace that seamlessly integrates cognitive psychology principles with cutting-edge generative AI technologies. It enables professionals, researchers, and learners to instantly analyze massive documents, visualize structural hierarchies, and seamlessly pivot information across custom business or research axes.

## Features
*   **Document Ingestion & Semantic Chunking**: Dynamically slice unstructured documents into intelligent `SemanticChunk` models that avoid abrupt "mid-sentence" cuts.
*   **Entity Extraction & Multi-Dimensional Tagging**: Automatically tag recognized entities and map content along custom domains like "Time axis" using NLP and Vision-Language Models.
*   **Robust LLM Integration via OpenRouter**: Seamlessly communicate with various AI models (Claude, GPT-4o, Gemini) through a unified interface.
*   **Network Resilience and High Availability**: Built-in automatic retries for transient network errors and intelligent model fallback mechanisms ensure your workflows never crash due to third-party API instability.
*   **Secure BYOK Configuration**: Bring Your Own Key (BYOK) support natively powered by OpenRouter. Your API keys are strictly validated and handled securely in memory.
*   **Dependency Injection Architecture**: Designed under the rigorous AC-CDD methodology, all external dependencies are decoupled, ensuring extreme stability and mock-free CI testing capabilities.
*   **Hybrid Execution Modes**: Supports running in local CI or offline environments gracefully using "Mock Mode," dynamically rerouting to functional deterministic models without complex infrastructure requirements.
*   **Configurable Model Routing**: Configure multiple distinct AI models optimized for different capabilities (e.g., text chunking vs logical reasoning tasks).

## Installation

Ensure you have Python 3.12+ installed. We use `uv` for lightning-fast package management.

```bash
# Clone the repository
git clone https://github.com/your-username/matome.git
cd matome

# Install dependencies using uv
uv sync
```

## Usage

Create a `.env` file in the root directory.

```dotenv
OPENROUTER_API_KEY=your_secret_key_here
TENANT_ID=your_org_id
```

Run the core application verification and interactive tutorial to explore configuration routing and DI execution:

```bash
uv run pytest tests/e2e/test_uat.py
```

## Project Structure

*   `src/domain_models/`: Core Pydantic schemas and configuration objects enforcing strict bounds.
*   `src/application/`: Application layer logic including the DI Container and Ingestion Pipeline orchestrator.
*   `src/interfaces/`: Abstract protocols defining system boundaries.
*   `src/infrastructure/`: Implementations of models, web transports, and local file processors.
*   `tests/`: Executable tests covering UAT, E2E integrations, and robust Unit logic.
