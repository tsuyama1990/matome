"""Centralized domain constants for application configuration defaults."""

DEFAULT_MAX_CHUNK_SCAN_SIZE = 10000
DEFAULT_FAST_MODEL = "google/gemini-2.5-flash"
DEFAULT_REASONING_MODEL = "anthropic/claude-3.7-sonnet"
DEFAULT_MULTIMODAL_MODEL = "openai/gpt-4o"

DEFAULT_LLM_SERVICE_PATH = "src.interfaces.LLMProtocol"
DEFAULT_DOCUMENT_SERVICE_PATH = "src.interfaces.DocumentProcessingService"
DEFAULT_GRAPH_SERVICE_PATH = "src.interfaces.KnowledgeGraphService"
DEFAULT_ACTIVE_LEARNING_SERVICE_PATH = "src.interfaces.ActiveLearningService"
