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
    r"(?i)base64",
    r"(?i)encoded\s+text",
    r"(?i)developer\s+mode",
    r"(?i)jailbreak",
    r"(?i)DAN\s+mode",
    r"(?i)unrestricted\s+mode",
]

SYSTEM_INJECTION_PATTERNS = [
    r"(?i)\b(DROP|DELETE|UPDATE|INSERT|ALTER)\s+(TABLE|FROM|INTO|DATABASE)\b",
    r"(?i)\b(rm|sudo|chmod|chown|wget|curl|nc|netcat)\s+",
    r"(?i)\b(cat|ls|pwd|whoami)\s+",
    r"(?i)/bin/sh",
    r"(?i)/bin/bash",
]

# Defaults
DEFAULT_TOKENIZER = "cl100k_base"
DEFAULT_EMBEDDING = "intfloat/multilingual-e5-large"
DEFAULT_SUMMARIZER = "gpt-4o"

# Configuration Defaults
LARGE_SCALE_THRESHOLD = 20000

# Chunking Defaults
DEFAULT_MAX_TOKENS = 500
DEFAULT_OVERLAP = 0
DEFAULT_SEMANTIC_CHUNKING_MODE = False
DEFAULT_SEMANTIC_CHUNKING_THRESHOLD = 0.8
DEFAULT_SEMANTIC_CHUNKING_PERCENTILE = 90

# Embedding Defaults
DEFAULT_EMBEDDING_BATCH_SIZE = 32

# Clustering Defaults
DEFAULT_RANDOM_STATE = 42
DEFAULT_UMAP_N_NEIGHBORS = 15
DEFAULT_UMAP_MIN_DIST = 0.1
DEFAULT_UMAP_N_COMPONENTS = 2
DEFAULT_CLUSTERING_WRITE_BATCH_SIZE = 1000
DEFAULT_CLUSTERING_PROBABILITY_THRESHOLD = 0.1
DEFAULT_CLUSTER_BATCH_SIZE = 20
DEFAULT_CHUNK_BUFFER_SIZE = 50

# Canvas Defaults
DEFAULT_CANVAS_NODE_WIDTH = 400
DEFAULT_CANVAS_NODE_HEIGHT = 200
DEFAULT_CANVAS_GAP_X = 50
DEFAULT_CANVAS_GAP_Y = 300

# Store Defaults
DEFAULT_STORE_WRITE_BATCH_SIZE = 1000
DEFAULT_STORE_READ_BATCH_SIZE = 500

# Interactive Defaults
DEFAULT_MAX_INSTRUCTION_LENGTH = 1000
DEFAULT_SERVER_PORT = 5006

# File Processing Defaults
DEFAULT_MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB

# Summarization Defaults
DEFAULT_MAX_SUMMARY_TOKENS = 200
DEFAULT_MAX_RETRIES = 3
DEFAULT_LLM_TEMPERATURE = 0.0
DEFAULT_MAX_WORD_LENGTH = 1000
DEFAULT_MAX_INPUT_LENGTH = 500_000

# Verification Defaults
DEFAULT_VERIFIER_ENABLED = True

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
