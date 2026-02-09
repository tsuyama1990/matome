# Cycle 01 User Acceptance Testing (UAT) Plan

## 1. Test Scenarios

### Scenario 01: Project Setup Verification (Priority: High)
*   **Goal**: Ensure the development environment is correctly configured.
*   **Inputs**: `uv` or `pip` installation command.
*   **Expected Outcome**: `pyproject.toml` dependencies are installed without conflicts. `pytest` runs successfully (even if tests are empty).

### Scenario 02: Text Ingestion & Cleaning (Priority: Medium)
*   **Goal**: Validate that text files can be read and normalized.
*   **Inputs**: A text file containing mixed full-width and half-width characters (e.g., `test_data/sample.txt`).
*   **Expected Outcome**: The output string is normalized (NFKC) and retains all meaningful content.

### Scenario 03: Japanese Sentence Splitting (Priority: High)
*   **Goal**: Validate the regex-based semantic chunker logic.
*   **Inputs**: A paragraph of Japanese text: `「これはテストです。」と彼は言った。次の文です！`
*   **Expected Outcome**: The text is split into sentences correctly:
    1.  `「これはテストです。」と彼は言った。`
    2.  `次の文です！`
    *   (Note: Ensure punctuation is kept attached to the sentence.)

### Scenario 04: Chunk Size Management (Priority: Medium)
*   **Goal**: Ensure chunks respect the token limit.
*   **Inputs**: A long text (2000 chars) and a `max_tokens` setting of 500 (~750 chars).
*   **Expected Outcome**: The result is a list of ~3 chunks, each roughly 750 chars or less, without breaking sentences mid-way.

## 2. Behavior Definitions (Gherkin)

```gherkin
Feature: Japanese Text Chunking

  Scenario: Splitting text at sentence boundaries
    GIVEN a Japanese text containing "句点（。）" and "感嘆符（！）"
    WHEN the text is processed by the SemanticChunker
    THEN the text should be split into multiple segments
    AND each segment should end with a punctuation mark
    AND no segment should start with a punctuation mark

  Scenario: Merging short sentences into a chunk
    GIVEN a list of short sentences ["Sentence A。", "Sentence B。", "Sentence C。"]
    AND a max_tokens limit that allows 2 sentences
    WHEN the chunker processes the sentences
    THEN the first chunk should contain "Sentence A。Sentence B。"
    AND the second chunk should contain "Sentence C。"

  Scenario: Handling text normalization
    GIVEN a text with full-width alphanumeric characters "１２３ＡＢＣ"
    WHEN the text is normalized
    THEN the result should be half-width "123ABC"
```
