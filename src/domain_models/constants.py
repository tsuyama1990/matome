from typing import Final

# Processing Defaults
DEFAULT_MAX_TOKENS: Final[int] = 1000
DEFAULT_OVERLAP: Final[int] = 100
DEFAULT_TOKENIZER: Final[str] = "cl100k_base"
DEFAULT_SEMANTIC_CHUNKING_MODE: Final[bool] = False
DEFAULT_SEMANTIC_CHUNKING_THRESHOLD: Final[float] = 0.5
DEFAULT_SEMANTIC_CHUNKING_PERCENTILE: Final[int] = 90

# Embedding Defaults
DEFAULT_EMBEDDING: Final[str] = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_BATCH_SIZE: Final[int] = 32

# Clustering Defaults
DEFAULT_UMAP_N_NEIGHBORS: Final[int] = 15
DEFAULT_UMAP_MIN_DIST: Final[float] = 0.1
DEFAULT_UMAP_N_COMPONENTS: Final[int] = 2
DEFAULT_CLUSTERING_WRITE_BATCH_SIZE: Final[int] = 1000
DEFAULT_CLUSTERING_PROBABILITY_THRESHOLD: Final[float] = 0.1
LARGE_SCALE_THRESHOLD: Final[int] = 10000
DEFAULT_CHUNK_BUFFER_SIZE: Final[int] = 1000

# Summarization Defaults
DEFAULT_SUMMARIZER: Final[str] = "gpt-4o-mini"
DEFAULT_MAX_SUMMARY_TOKENS: Final[int] = 200
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_LLM_TEMPERATURE: Final[float] = 0.0
DEFAULT_MAX_WORD_LENGTH: Final[int] = 500
DEFAULT_MAX_INPUT_LENGTH: Final[int] = 100_000

# Verification Defaults
DEFAULT_VERIFIER_ENABLED: Final[bool] = False

# Store Defaults
DEFAULT_STORE_WRITE_BATCH_SIZE: Final[int] = 1000
DEFAULT_STORE_READ_BATCH_SIZE: Final[int] = 500

# Interactive Defaults
DEFAULT_SERVER_PORT: Final[int] = 5006
DEFAULT_MAX_INSTRUCTION_LENGTH: Final[int] = 1000
DEFAULT_MAX_FILE_SIZE_BYTES: Final[int] = 500 * 1024 * 1024  # 500MB

# Canvas Export Defaults
DEFAULT_CANVAS_NODE_WIDTH: Final[int] = 400
DEFAULT_CANVAS_NODE_HEIGHT: Final[int] = 200
DEFAULT_CANVAS_GAP_X: Final[int] = 50
DEFAULT_CANVAS_GAP_Y: Final[int] = 100

# Security Patterns
PROMPT_INJECTION_PATTERNS: Final[list[str]] = [
    r"ignore previous instructions",
    r"system prompt",
    r"you are a",
]

# Validation
VALID_NODE_ID_PATTERN_STR: Final[str] = r"^[a-zA-Z0-9_\-]+$"

# Allowed Models (Whitelist)
ALLOWED_EMBEDDING_MODELS: Final[set[str]] = {
    "sentence-transformers/all-MiniLM-L6-v2",
    "text-embedding-3-small",
    "text-embedding-3-large",
}

ALLOWED_SUMMARIZATION_MODELS: Final[set[str]] = {
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-5-sonnet",
    "claude-3-haiku",
    "meta-llama/llama-3-8b-instruct",
}

ALLOWED_TOKENIZER_MODELS: Final[set[str]] = {
    "cl100k_base",
    "p50k_base",
    "r50k_base",
}
