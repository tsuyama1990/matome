from typing import Final

# Constants for DB Schema
MAX_DB_CONTENT_LENGTH: Final[int] = 10_000_000

# Constants for Processing
DEFAULT_MAX_TOKENS: Final[int] = 1000
DEFAULT_OVERLAP: Final[int] = 100
DEFAULT_SEMANTIC_CHUNKING_MODE: Final[bool] = False
DEFAULT_SEMANTIC_CHUNKING_THRESHOLD: Final[float] = 0.5
DEFAULT_SEMANTIC_CHUNKING_PERCENTILE: Final[int] = 90
DEFAULT_EMBEDDING: Final[str] = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_BATCH_SIZE: Final[int] = 32
DEFAULT_RANDOM_STATE: Final[int] = 42
DEFAULT_UMAP_N_NEIGHBORS: Final[int] = 15
DEFAULT_UMAP_MIN_DIST: Final[float] = 0.1
DEFAULT_UMAP_N_COMPONENTS: Final[int] = 2
DEFAULT_CLUSTERING_WRITE_BATCH_SIZE: Final[int] = 1000
DEFAULT_CLUSTERING_PROBABILITY_THRESHOLD: Final[float] = 0.1
LARGE_SCALE_THRESHOLD: Final[int] = 10000
DEFAULT_CLUSTER_BATCH_SIZE: Final[int] = 10
DEFAULT_CHUNK_BUFFER_SIZE: Final[int] = 1000
DEFAULT_CANVAS_NODE_WIDTH: Final[int] = 400
DEFAULT_CANVAS_NODE_HEIGHT: Final[int] = 200
DEFAULT_CANVAS_GAP_X: Final[int] = 50
DEFAULT_CANVAS_GAP_Y: Final[int] = 100
DEFAULT_STORE_WRITE_BATCH_SIZE: Final[int] = 1000
DEFAULT_STORE_READ_BATCH_SIZE: Final[int] = 500
DEFAULT_IO_BUFFER_SIZE: Final[int] = 65536
DEFAULT_MAX_INSTRUCTION_LENGTH: Final[int] = 1000
DEFAULT_SERVER_PORT: Final[int] = 5006
DEFAULT_MAX_FILE_SIZE_BYTES: Final[int] = 500 * 1024 * 1024  # 500 MB
DEFAULT_REFINEMENT_LIMIT_MULTIPLIER: Final[int] = 2
DEFAULT_UI_MAX_SOURCE_CHUNKS: Final[int] = 100
DEFAULT_UI_MAX_CHILDREN: Final[int] = 50
DEFAULT_MAX_REFINEMENT_HISTORY: Final[int] = 10
DEFAULT_SUMMARIZER: Final[str] = "openai/gpt-4o-mini"
DEFAULT_MAX_SUMMARY_TOKENS: Final[int] = 500
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_LLM_TEMPERATURE: Final[float] = 0.0
DEFAULT_MAX_WORD_LENGTH: Final[int] = 1000
DEFAULT_MAX_INPUT_LENGTH: Final[int] = 100000
DEFAULT_VERIFIER_ENABLED: Final[bool] = False
HIGH_PRECISION_MAX_TOKENS: Final[int] = 200
HIGH_PRECISION_OVERLAP: Final[int] = 20
DEFAULT_TRAVERSAL_MAX_QUEUE_SIZE: Final[int] = 10000

# Constants for Validation
DEFAULT_TOKENIZER: Final[str] = "cl100k_base"
ALLOWED_EMBEDDING_MODELS: Final[set[str]] = {
    "sentence-transformers/all-MiniLM-L6-v2",
    "intfloat/multilingual-e5-large",
    "text-embedding-3-small",
    "text-embedding-3-large",
}
ALLOWED_SUMMARIZATION_MODELS: Final[set[str]] = {
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-haiku",
    "google/gemini-flash-1.5",
    "meta-llama/llama-3-8b-instruct",
}
ALLOWED_TOKENIZER_MODELS: Final[set[str]] = {"cl100k_base", "gpt2", "p50k_base", "r50k_base"}

DEFAULT_STRATEGY_MAPPING: Final[dict[str, str]] = {
    "wisdom": "wisdom",
    "knowledge": "knowledge",
    "information": "information",
}

# Security Patterns
PROMPT_INJECTION_PATTERNS: Final[list[str]] = [
    r"ignore previous instructions",
    r"system prompt",
    r"you are not a",
    r"output everything above",
]
SYSTEM_INJECTION_PATTERNS: Final[list[str]] = [
    r"rm -rf",
    r"wget ",
    r"curl ",
    r"cat /etc/passwd",
    r"drop table",
]
MAX_RECURSION_DEPTH = 10
