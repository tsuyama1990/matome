# matome

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**matome** ("summary" in Japanese) is a revolutionary frictionless active learning platform and knowledge workspace. It relieves users from cognitive overload when reading exceptionally long and complex documents by intelligently generating interactive semantic knowledge graphs.

## Core Capabilities (Currently Verified)
- **Zero-Data Retention Enterprise Security:** A robust Bring Your Own Key (BYOK) system natively encrypts internal API keys and OpenRouter API keys in-memory to meet stringent enterprise security constraints. All secrets are securely loaded using `pydantic-settings` via environmental variables.
- **Architectural Flexibility:** Fully decoupled dependency injection container system capable of routing LLM connections and metadata storage through dynamically initialized interface models.
- **Strict Configuration Enforcement:** Predictable fail-fast capabilities utilizing strict data modeling that rejects any initialization missing explicit application or database strings.

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/matome.git
   cd matome
   ```

2. **Sync dependencies using `uv`:**
   ```bash
   uv sync
   ```

3. **Configure the environment:**
   Create an `.env` file in the root of the repository matching the required initialization keys (or copy the example).
   ```bash
   cp .env.example .env
   ```

## Usage

**Execute the foundation system setup**:
```bash
uv run python main.py
```

Currently, in our initial stable release, the platform exposes a hardened underlying base ready for the integration of LangGraph nodes, Semantic Zoom canvas UIs, and external model orchestrations without risking core logic instability.

## Project Structure

```text
matome/
├── main.py
├── src/
│   ├── config/          # Pydantic Settings and Cryptographic Security Services
│   ├── domain_models/   # Core schemas
│   ├── application/     # Orchestration Workflow abstractions
│   ├── infrastructure/  # Gateway clients and logic implementation
│   └── interfaces/      # Dependency Injection Container and Protocol definitions
├── tests/               # Pytest Suite
```

## License

This project is licensed under the MIT License.