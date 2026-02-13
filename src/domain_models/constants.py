# DB Schema Constants
TABLE_NODES = "nodes"
COL_ID = "id"
COL_TYPE = "type"
COL_CONTENT = "content"  # Stores JSON of the node (excluding embedding)
COL_EMBEDDING = "embedding"  # Stores JSON of the embedding list

# Prompt Injection Patterns
PROMPT_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"system prompt",
    r"you are a large language model",
]

# Config Constants
ALLOWED_EMBEDDING_MODELS = {
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
    "intfloat/multilingual-e5-large",
    "mock-model",  # Added for mock testing
}

ALLOWED_SUMMARIZATION_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "openai/gpt-4o-mini",  # Added for CLI tests
}

# Usually same as embedding models for tiktoken compatibility
ALLOWED_TOKENIZER_MODELS = ALLOWED_EMBEDDING_MODELS | ALLOWED_SUMMARIZATION_MODELS | {"o200k_base", "cl100k_base"}

DEFAULT_MAX_INPUT_LENGTH = 100_000
DEFAULT_MAX_WORD_LENGTH = 100

# Canvas Constants
DEFAULT_CANVAS_GAP_X = 200
DEFAULT_CANVAS_GAP_Y = 200
DEFAULT_CANVAS_CARD_WIDTH = 400
DEFAULT_CANVAS_CARD_HEIGHT = 400
DEFAULT_CANVAS_NODE_WIDTH = 400
DEFAULT_CANVAS_NODE_HEIGHT = 200
DEFAULT_CANVAS_GROUP_COLOR = "1"

# UAT Constants
DEFAULT_EMBEDDING = "intfloat/multilingual-e5-large"
DEFAULT_SUMMARIZATION = "gpt-4o"
DEFAULT_SUMMARIZER = "gpt-4o"
DEFAULT_TOKENIZER = "gpt-4o"

# Algorithm Constants
LARGE_SCALE_THRESHOLD = 50
