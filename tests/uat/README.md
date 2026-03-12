# UAT (User Acceptance Testing) Roadmap

This directory contains the testing infrastructure for User Acceptance Testing (UAT) corresponding to the scenarios defined in `dev_documents/USER_TEST_SCENARIO.md`.

## Execution Plan
UAT scripts are highly dependent on the complete functional integration of AI models and the vector database. As such, they will be implemented in later development cycles once the underlying architecture is operational.

### Cycle Mapping
- **Cycle 03 (LLM Gateway & Chunking):** UAT scenarios testing document ingestion and semantic chunking boundaries.
- **Cycle 04 (RAPTOR Engine):** UAT scenarios covering the mathematical tree generation from dense chunks.
- **Cycle 05 (SQ3R Interaction):** UAT scripts validating the interactive question/answer loop and sandwich feedback mechanism.
- **Cycle 06 (MD-SKJ Pivot):** UAT validation for vector search filtering, multi-dimensional axes pivoting, and export formatting.

## Prerequisites
Before executing these tests, ensure:
1. Valid OpenRouter API keys are present (for "Real Mode").
2. The operational database is configured.
3. The underlying LLM and vector store DI singletons are properly registered in the environment.
