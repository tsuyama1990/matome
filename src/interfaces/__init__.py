"""
Interfaces layer defining structural protocols and the Dependency Injection logic.
"""

from src.interfaces.dependencies import (
    DIContainer,
    LLMProtocol,
    VectorStoreProtocol,
    bootstrap_application_services,
)

__all__ = ["DIContainer", "LLMProtocol", "VectorStoreProtocol", "bootstrap_application_services"]
from src.interfaces.llm_protocol import LLMProtocol

__all__.append("LLMProtocol")
