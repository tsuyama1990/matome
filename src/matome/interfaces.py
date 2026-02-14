from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster
from domain_models.types import DIKWLevel


class PromptStrategy(ABC):
    """
    Abstract Base Class for DIKW prompt strategies.
    Defines how to construct prompts for different levels of abstraction.
    """

    @abstractmethod
    def format_prompt(self, text: str, context: dict[str, Any] | None = None) -> str:
        """
        Constructs the prompt for the LLM.

        Args:
            text: The combined text to be summarized.
            context: Optional context dictionary (e.g. instructions, metadata).

        Returns:
            The formatted prompt string.
        """
        ...

    @property
    @abstractmethod
    def dikw_level(self) -> DIKWLevel:
        """Returns the target DIKW level."""
        ...


@runtime_checkable
class Chunker(Protocol):
    """
    Protocol for text chunking engines.
    """

    def split_text(
        self, text: str | Iterable[str], config: ProcessingConfig
    ) -> Iterable[Chunk]:
        """
        Split text into chunks.
        Accepts either a full string or an iterable of strings (streaming).
        """
        ...


@runtime_checkable
class Clusterer(Protocol):
    """
    Protocol for clustering engines.
    """

    def cluster_nodes(
        self, embeddings: Iterable[list[float]], config: ProcessingConfig
    ) -> list[Cluster]:
        """
        Cluster nodes based on embeddings.
        """
        ...


@runtime_checkable
class Summarizer(Protocol):
    """
    Protocol for summarization engines.
    """

    def summarize(
        self,
        text: str,
        config: ProcessingConfig,
        strategy: PromptStrategy | None = None,
    ) -> str:
        """
        Summarize the provided text.

        Args:
            text: The text to summarize.
            config: Configuration parameters.
            strategy: Optional PromptStrategy to control summarization style.

        Returns:
            The summary text.
        """
        ...
