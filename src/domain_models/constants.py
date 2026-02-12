"""
Centralized constants for the Matome project.
Includes security patterns, defaults, and configuration whitelists.
"""

# Security / Validation
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)ignore\s+all\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)simulated\s+response",
]

# Defaults
DEFAULT_TOKENIZER = "cl100k_base"
DEFAULT_EMBEDDING = "intfloat/multilingual-e5-large"
DEFAULT_SUMMARIZER = "gpt-4o"
DEFAULT_DIKW_LEVEL = "data"

# Configuration Defaults
LARGE_SCALE_THRESHOLD = 20000

# Canvas Defaults
DEFAULT_CANVAS_NODE_WIDTH = 400
DEFAULT_CANVAS_NODE_HEIGHT = 200
DEFAULT_CANVAS_GAP_X = 50
DEFAULT_CANVAS_GAP_Y = 300

# Security Whitelists
ALLOWED_TOKENIZER_MODELS = {
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

ALLOWED_EMBEDDING_MODELS = {
    "intfloat/multilingual-e5-large",
    "intfloat/multilingual-e5-small",
    "intfloat/multilingual-e5-base",
    "openai/text-embedding-ada-002",
    "openai/text-embedding-3-small",
    "openai/text-embedding-3-large",
    "mock-model",  # Allowed for testing
}

ALLOWED_SUMMARIZATION_MODELS = {
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

# Regex Patterns
SENTENCE_SPLIT_PATTERN = r"(?<=[。！？])\s*|\n+"
