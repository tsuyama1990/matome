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
   git clone https://github.com/tsuyama1990/matome.git
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

## Features
- **Semantic Chunking:** Context-preserving noise normalization and semantic chunking of massive text data.
- **RAPTOR Tree Generation:** Hierarchical clustering (UMAP+GMM) to summarize documents dynamically from bottom up.
- **Interactive Active Learning (SQ3R):** Unlock knowledge nodes by answering AI-generated questions and reciting information to solidify memory.
- **MD-SKJ Pivot Engine:** Dynamically re-arrange clustered knowledge along custom, multi-dimensional business axes (e.g., actors vs. state transitions) to instantly output actionable UML diagrams and Markdown Requirements.

## Usage

**Execute the foundation system setup**:
```bash
uv run python main.py
```

**Testing the end-to-end capabilities**:
```bash
uv run pytest
```

Currently, the platform exposes a hardened underlying base fully capable of handling LangGraph node orchestration, Semantic Zoom API generation, SQ3R active learning verification, and multi-dimensional Pivot KJ insights.

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

## txt2speech: textbook text to chapter MP3s (local, offline)

Converts `.txt` / `.md` into one MP3 per chapter with a local [VOICEVOX Engine](https://github.com/VOICEVOX/voicevox_engine) (nothing leaves the machine; the engine URL must be loopback).

**Prerequisites**: FFmpeg 5 or newer on `PATH` (or `--ffmpeg /path/to/ffmpeg`) and a running VOICEVOX Engine (default `http://127.0.0.1:50021`; for the GPU use the `nvidia` image, e.g. `docker run --rm --gpus all -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:nvidia-latest`).

```bash
uv run python -m src.txt2speech textbook.md -o out/ --speaker 1 --album "My Textbook"
# options: --config config.yaml --engine-url --speed-scale 1.1 --max-chars 80 --ffmpeg --cover cover.jpg --voice-name VOICEVOX --dictionary terms.csv
```

Output: `out/01_<heading>.mp3`, `out/02_<heading>.mp3`, ... (one path per line on stdout; progress on stderr). Exit codes: 0 ok, 2 bad input or settings, 3 engine or FFmpeg failure. An interrupted run resumes from the progress file in `out/` when rerun with the same input and settings; temporary WAVs are removed once a chapter's MP3 is complete.

`config.yaml` keys match the `Settings` fields in `src/txt2speech/config.py` (speaker, speed_scale, pitch_scale, pause_ms, bitrate, dictionaries, cover, album, voice_name, ffmpeg_path, ...). Dictionary CSV columns: surface, katakana reading, accent position (header row first).

**Manual checks on real hardware** (not covered by automated tests, which use a fake engine): real-time factor <= 0.20, VRAM <= 4 GB during a 100,000-character run, audio quality, and intelligibility at 1.2x playback. The design and test plans are in `.specs/REQ-2026-002/`; deferred items are in its `backlog.md`.
