"""
Default configuration constants for the Matome system.
These values are used as fallbacks when environment variables are not set.
"""

# Text Processing Defaults
DEFAULT_MAX_TOKENS = 500
DEFAULT_OVERLAP = 0
DEFAULT_TOKENIZER_MODEL = "cl100k_base"

# Semantic Chunking Defaults
DEFAULT_SEMANTIC_CHUNKING_MODE = False
DEFAULT_SEMANTIC_CHUNKING_THRESHOLD = 0.8
DEFAULT_SEMANTIC_CHUNKING_PERCENTILE = 90

# Embedding Defaults
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
DEFAULT_EMBEDDING_BATCH_SIZE = 32

# Clustering Defaults
DEFAULT_CLUSTERING_ALGORITHM = "gmm"
DEFAULT_N_CLUSTERS = None  # None indicates auto-detection
DEFAULT_RANDOM_STATE = 42
DEFAULT_UMAP_N_NEIGHBORS = 15
DEFAULT_UMAP_MIN_DIST = 0.1

# Summarization Defaults
DEFAULT_SUMMARIZATION_MODEL = "gpt-4o"
DEFAULT_MAX_SUMMARY_TOKENS = 200
DEFAULT_MAX_RETRIES = 3
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
