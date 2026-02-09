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
