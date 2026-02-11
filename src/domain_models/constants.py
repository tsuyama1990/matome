"""
Centralized constants for the Matome project.
Includes security patterns, defaults, and configuration whitelists.
"""

from typing import Final

# Security / Validation
PROMPT_INJECTION_PATTERNS: Final[list[str]] = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)ignore\s+all\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)simulated\s+response",
]

# Defaults
DEFAULT_TOKENIZER: Final[str] = "cl100k_base"
DEFAULT_EMBEDDING: Final[str] = "intfloat/multilingual-e5-large"
DEFAULT_SUMMARIZER: Final[str] = "gpt-4o"
DEFAULT_DEBUG_EMBEDDING_MODEL: Final[str] = "all-MiniLM-L6-v2"

# Configuration Defaults
LARGE_SCALE_THRESHOLD: Final[int] = 20000

# Canvas Node Types
CANVAS_NODE_TYPE_TEXT: Final[str] = "text"
CANVAS_NODE_TYPE_FILE: Final[str] = "file"
CANVAS_NODE_TYPE_GROUP: Final[str] = "group"

# Security Whitelists
ALLOWED_TOKENIZER_MODELS: Final[frozenset[str]] = frozenset(
    {
        "cl100k_base",
        "p50k_base",
        "r50k_base",
        "gpt2",
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4o",
        "text-embedding-ada-002",
        "text-embedding-3-small",
        "text-embedding-3-large",
    }
)

ALLOWED_EMBEDDING_MODELS: Final[frozenset[str]] = frozenset(
    {
        "intfloat/multilingual-e5-large",
        "intfloat/multilingual-e5-small",
        "intfloat/multilingual-e5-base",
        "openai/text-embedding-ada-002",
        "openai/text-embedding-3-small",
        "openai/text-embedding-3-large",
        "mock-model",  # Allowed for testing
    }
)

ALLOWED_SUMMARIZATION_MODELS: Final[frozenset[str]] = frozenset(
    {
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "google/gemini-1.5-flash",
        "google/gemini-1.5-pro",
        "anthropic/claude-3-opus",
        "anthropic/claude-3-sonnet",
        "anthropic/claude-3-haiku",
        "meta-llama/llama-3-70b-instruct",
        "openai/gpt-4o",  # OpenRouter format
        "openai/gpt-4o-mini",
        "mock-model",
    }
)

# Regex Patterns
SENTENCE_SPLIT_PATTERN: Final[str] = r"(?<=[。！？])\s*|\n+"  # noqa: RUF001

# Debug Messages
DEBUG_MSG_CUDA_AVAILABLE: Final[str] = "CUDA available: {}"
DEBUG_MSG_CUDA_COUNT: Final[str] = "CUDA device count: {}"
DEBUG_MSG_CURRENT_DEVICE: Final[str] = "Current device: {}"
DEBUG_MSG_DEVICE_NAME: Final[str] = "Device name: {}"
DEBUG_MSG_INIT_MODEL: Final[str] = "\nInitializing SentenceTransformer (auto-detect)..."
DEBUG_MSG_MODEL_DEVICE: Final[str] = "Model device: {}"
