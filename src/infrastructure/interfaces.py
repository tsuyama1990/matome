"""Abstract interfaces for repository and gateway."""

from abc import ABC, abstractmethod


class AbstractVectorRepository(ABC):
    """Abstract interface for Vector Database."""

    @abstractmethod
    def health_check(self) -> bool:
        """Perform a health check on the Vector Database."""


class AbstractLLMGateway(ABC):
    """Abstract interface for LLM Gateway."""

    @abstractmethod
    def health_check(self) -> bool:
        """Perform a health check on the LLM Gateway."""
