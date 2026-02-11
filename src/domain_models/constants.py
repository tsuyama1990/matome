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

# Configuration Defaults
LARGE_SCALE_THRESHOLD: Final[int] = 20000

# Canvas Defaults
DEFAULT_CANVAS_NODE_WIDTH: Final[int] = 400
DEFAULT_CANVAS_NODE_HEIGHT: Final[int] = 200
DEFAULT_CANVAS_GAP_X: Final[int] = 50
DEFAULT_CANVAS_GAP_Y: Final[int] = 300

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
