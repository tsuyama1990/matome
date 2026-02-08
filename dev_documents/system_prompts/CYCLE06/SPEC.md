# Cycle 06 Specification: Verification & Final Polish

## 1. Summary

The final cycle focuses on ensuring the reliability and usability of the system. We implement a **Verification Module** based on the Chain-of-Verification (CoVe) and Context-Aware Hierarchical Merging (CAHM) concepts. This module cross-checks the generated summaries against their source chunks to detect and flag potential hallucinations. Additionally, we will polish the **Command Line Interface (CLI)** to provide a smooth user experience, including progress bars, model selection, and clear error messages. This cycle concludes with the final End-to-End (E2E) testing.

## 2. System Architecture

Finalizing the codebase.

```
.
├── dev_documents/
├── src/
│   └── matome/
│       ├── agents/
│       │   ├── **verifier.py** # Hallucination Checker
│       │   └── ...
│       ├── **cli.py**          # Enhanced CLI
│       └── ...
├── tests/
│   └── **test_verifier.py**
└── pyproject.toml
```

## 3. Design Architecture

### 3.1. Verification Agent (`src/matome/agents/verifier.py`)

*   **Class**: `VerifierAgent`
*   **Method**: `verify(summary: str, source_text: str) -> VerificationResult`
    *   **Logic**:
        1.  Extract entities from summary (Using LLM or SpaCy).
        2.  Check if these entities exist in the source text.
        3.  Ask LLM: "Is the statement '[sentence]' supported by the text?"
    *   **Output**: A score (0.0 to 1.0) and a list of unsupported claims.

### 3.2. CLI (`src/matome/cli.py`)

*   **Commands**:
    *   `matome run <file> --model <name>`: Run full pipeline.
    *   `matome export <file> --format <canvas|md>`: Export results.
*   **Features**:
    *   `tqdm` progress bars for chunking and clustering steps.
    *   Argument parsing with `typer` or `argparse`.
    *   Graceful handling of API errors and interruptions.

## 4. Implementation Approach

1.  **Verifier Implementation**:
    *   Implement a simplified CoVe: Ask the LLM to list facts in the summary and verify each against the source.
    *   If a fact is unsupported, flag it (or in a more advanced version, regenerate the summary).
2.  **CLI Polish**:
    *   Use `typer` for a modern CLI experience.
    *   Add logging configuration (verbose vs quiet).
3.  **Documentation**:
    *   Finalize the `README.md` with usage instructions.
    *   Ensure all docstrings are up to date.

## 5. Test Strategy

### 5.1. Unit Testing
*   **Target**: `src/matome/agents/verifier.py`
    *   **Test Case**: Provide a summary "The sky is green" and source "The sky is blue".
    *   **Expected**: Verification score should be low.
    *   **Test Case**: Provide a summary "The sky is blue" and source "The sky is blue".
    *   **Expected**: Verification score should be high.

### 5.2. Integration Testing (E2E)
*   **Scenario**: Run the full pipeline via CLI on `test_data/sample.txt`.
    *   Command: `matome run test_data/sample.txt --output-dir results`
    *   Verify `results/summary_all.md` and `results/summary_kj.json` exist.
    *   Verify the process completes without crashing.
