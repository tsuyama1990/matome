DEBUG_MSG_CUDA_AVAILABLE = "CUDA available: {}"
DEBUG_MSG_CUDA_COUNT = "Number of GPUs: {}"
DEBUG_MSG_CURRENT_DEVICE = "Current device ID: {}"
DEBUG_MSG_DEVICE_NAME = "Device name: {}"
DEBUG_MSG_INIT_MODEL = "Initializing SentenceTransformer model..."
DEBUG_MSG_MODEL_DEVICE = "Model loaded on device: {}"
DEFAULT_DEBUG_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Existing constants
ALLOWED_EMBEDDING_MODELS = {
    "all-MiniLM-L6-v2",
    "intfloat/multilingual-e5-large",
    "cl-tohoku/bert-base-japanese-v3",
    "pkshatech/GLuCoSE-base-ja",
    "text-embedding-3-small",  # OpenAI
}

ALLOWED_SUMMARIZATION_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-5-sonnet-20240620",
    "claude-3-haiku-20240307",
    "meta-llama/llama-3-8b-instruct",
}

ALLOWED_TOKENIZER_MODELS = {
    "cl100k_base",
    "p50k_base",
    "r50k_base",
    "gpt2",
}

DEFAULT_EMBEDDING = "intfloat/multilingual-e5-large"
DEFAULT_SUMMARIZER = "gpt-4o"
DEFAULT_TOKENIZER = "cl100k_base"

# Thresholds
LARGE_SCALE_THRESHOLD = 5000  # Number of nodes to switch to approximate clustering
PROMPT_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"forget the above",
    r"system prompt",
    r"you are not",
    r"output everything above",
    r"ignore all instructions",
    r"raw markdown",
    r"as an ai language model",
]

# Regex
SENTENCE_SPLIT_PATTERN = r"(?<=[。！？])\s*|\n+"  # noqa: RUF001
