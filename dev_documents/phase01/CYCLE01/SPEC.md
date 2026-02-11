# Cycle 01 Specification: Foundation & Semantic Chunking

## 1. Summary

This cycle focuses on establishing the project's foundation and implementing the core text processing capabilities. The primary goal is to set up the development environment, define the fundamental data structures using Pydantic, and build a robust "Semantic Chunking" engine optimized for Japanese text. This engine will serve as the input for all subsequent processing steps (embedding, clustering, summarization). By the end of this cycle, the system should be able to ingest a raw text file and decompose it into semantically coherent chunks based on sentence boundaries and token limits.

## 2. System Architecture

The following file structure represents the initial state of the project. **Bold files** indicate new creations or significant modifications in this cycle.

```
.
├── dev_documents/
├── src/
│   ├── **domain_models/**      # Core Pydantic models (Modularized)
│   │   ├── **__init__.py**
│   │   ├── **config.py**       # Configuration management
│   │   └── **manifest.py**     # Data structures (Chunk, Document)
│   └── matome/
│       ├── **__init__.py**
│       ├── **engines/**
│       │   ├── **__init__.py**
│       │   └── **chunker.py**  # Japanese-optimized semantic chunker
│       └── **utils/**
│           ├── **__init__.py**
│           ├── **text.py**     # Regex patterns and text normalization
│           └── **io.py**       # File reading helper
├── **tests/**
│   ├── **__init__.py**
│   ├── **test_chunker.py**     # Unit tests for chunking logic
│   └── **test_text_utils.py**  # Unit tests for regex patterns
├── **pyproject.toml**          # Project dependencies and tool config
└── **README.md**
```

## 3. Design Architecture

### 3.1. Domain Models (`src/domain_models/`)

We will use Pydantic V2 for strict type validation.

*   **`manifest.py`**:
    *   **`Document`**: Represents the raw input file.
        *   `content`: `str` (Full text)
        *   `metadata`: `dict` (Filename, path, etc.)
    *   **`Chunk`**: Represents a segment of text.
        *   `index`: `int` (Sequential ID)
        *   `text`: `str` (The actual content)
        *   `start_char_idx`: `int` (Position in original text)
        *   `end_char_idx`: `int`
        *   `metadata`: `dict` (Optional extra info)
*   **`config.py`**:
    *   **`ProcessingConfig`**: Configuration for chunking and other processes.
        *   `max_tokens`: `int` (Default 500)
        *   `overlap`: `int` (Default 0, optional for now)

### 3.2. Text Utilities (`src/matome/utils/text.py`)

This module encapsulates the logic for Japanese sentence boundary detection.
*   **Regex Pattern**: `(?<=[。！？])\s*|\n+` (Split after punctuation or on newlines).
*   **Normalization**: `unicodedata.normalize('NFKC', text)` to handle full-width/half-width variations.

### 3.3. Semantic Chunker (`src/matome/engines/chunker.py`)

*   **Class**: `JapaneseSemanticChunker`
*   **Method**: `split_text(text: str, config: ProcessingConfig) -> List[Chunk]`
    *   **Logic**:
        1.  Normalize the text.
        2.  Split text into sentences using the regex.
        3.  Iteratively merge sentences into chunks until the `max_tokens` limit is reached.
        4.  (Future hook: In Cycle 02, we will add embedding similarity checks here, but for Cycle 01, we stick to size-based semantic merging).

## 4. Implementation Approach

1.  **Project Initialization**:
    *   Set up `pyproject.toml` with `ruff`, `mypy`, `pytest`.
    *   Create the directory structure.
2.  **Domain Modeling**:
    *   Implement `Document` and `Chunk` classes in `src/domain_models/manifest.py`.
    *   Implement configuration in `src/domain_models/config.py`.
3.  **Utility Implementation**:
    *   Implement `normalize_text` and `split_sentences` in `src/matome/utils/text.py`.
    *   Verify regex behavior against tricky Japanese sentences (e.g., brackets `「...」` containing punctuation).
4.  **Chunker Logic**:
    *   Implement `JapaneseSemanticChunker` in `src/matome/engines/chunker.py`.
    *   Ensure it respects the token limit (using a simple character estimation for now: 1 token ≈ 1-1.5 chars, or use `tiktoken` if feasible).
5.  **Testing**:
    *   Write unit tests to verify that sentences are not split in the middle.
    *   Verify that chunk sizes are within limits.

## 5. Test Strategy

### 5.1. Unit Testing
*   **Target**: `src/matome/utils/text.py`
    *   **Test Case**: Input specific strings with mixed punctuation. Ensure split occurs *after* `。` and not before.
    *   **Test Case**: Check behavior with nested quotes (Note: Regex might need adjustment if strict quote handling is required, but simple splitting is acceptable for Cycle 01).
*   **Target**: `src/matome/engines/chunker.py`
    *   **Test Case**: Feed a long text (1000+ chars). Verify output is a list of `Chunk` objects.
    *   **Test Case**: Verify `Chunk.index` is sequential.

### 5.2. Integration Testing
*   **Scenario**: Load a real file (from `dev_documents/ALL_SPEC.md` for example), pass it to `Chunker`, and verify no text is lost (Concatenated chunks == Normalized input).
