"""Centralized domain constants for application configuration defaults."""

DEFAULT_MAX_CHUNK_SCAN_SIZE = 10000
DEFAULT_FAST_MODEL = "google/gemini-2.5-flash"
DEFAULT_REASONING_MODEL = "anthropic/claude-3.7-sonnet"
DEFAULT_MULTIMODAL_MODEL = "openai/gpt-4o"

DEFAULT_LLM_SERVICE_PATH = "src.interfaces.LLMProtocol"
DEFAULT_DOCUMENT_SERVICE_PATH = "src.interfaces.DocumentProcessingService"
DEFAULT_GRAPH_SERVICE_PATH = "src.interfaces.BaseTestKnowledgeGraphService"
DEFAULT_ACTIVE_LEARNING_SERVICE_PATH = "src.interfaces.BaseTestActiveLearningService"

DEFAULT_APP_DOMAIN = "https://matome.test"
DEFAULT_APP_TITLE = "matome"
DEFAULT_MAX_PROMPT_LENGTH = 1000000
DEFAULT_REQUESTS_PER_MINUTE_LIMIT = 60
DEFAULT_OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MAX_RESPONSE_BYTES = 1048576

DEFAULT_ALLOWED_API_DOMAINS = ["https://openrouter.ai"]
DEFAULT_CRYPTO_HASH_ALGORITHM = "sha256"
