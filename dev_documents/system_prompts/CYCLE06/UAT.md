# Cycle 06 User Acceptance Testing (UAT) Plan

## 1. Test Scenarios

### Scenario 16: Hallucination Detection (Priority: Medium)
*   **Goal**: Ensure the system flags unsupported claims.
*   **Inputs**: A summary containing "There are 5 planets" but the source says "There are 8 planets".
*   **Expected Outcome**: The VerifierAgent returns a warning or low confidence score.

### Scenario 17: CLI Usability Check (Priority: High)
*   **Goal**: Ensure the command-line tool is intuitive and informative.
*   **Inputs**: Running `matome --help`.
*   **Expected Outcome**: Clear instructions on how to use `run`, `export`, and set options like `--model`.
*   **Inputs**: Running `matome run missing_file.txt`.
*   **Expected Outcome**: A clear error message "File not found: missing_file.txt" (not a Python traceback).

### Scenario 18: Full End-to-End Test (Priority: High)
*   **Goal**: Verify the entire workflow from ingestion to export.
*   **Inputs**: The "Company Shikiho" text file.
*   **Expected Outcome**:
    1.  Chunking completes.
    2.  Clustering completes.
    3.  Summarization completes (RAPTOR tree built).
    4.  Verification runs.
    5.  Final files are saved.
    6.  Process takes < 10 mins (if using fast models/mock).

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Verification and CLI

  Scenario: Verifying a summary against source text
    GIVEN a summary and its source text
    WHEN the VerifierAgent checks the summary
    THEN it should identify if any statements in the summary are not supported by the source
    AND return a verification score

  Scenario: Running the CLI application
    GIVEN a valid input file path
    WHEN the user runs the `matome run` command
    THEN the system should display progress indicators
    AND generate the output files in the specified directory
    AND handle any errors gracefully without crashing
```
