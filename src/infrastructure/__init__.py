from src.domain_models import PipelineConfig
from src.interfaces import LLMProtocol, VectorDBProtocol

from .mock_vdb import MockVectorDB
from .openrouter import OpenRouterGateway


def get_openrouter_gateway(config: PipelineConfig) -> LLMProtocol:
    """Factory function for OpenRouterGateway."""
    return OpenRouterGateway(config)


def get_mock_vector_db() -> VectorDBProtocol:
    """Factory function for MockVectorDB."""
    return MockVectorDB()


__all__ = ["get_mock_vector_db", "get_openrouter_gateway"]
