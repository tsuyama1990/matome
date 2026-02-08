from typing import Protocol, runtime_checkable

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster


@runtime_checkable
class Chunker(Protocol):
    """Protocol for text chunking engines."""

    def split_text(self, text: str, config: ProcessingConfig) -> list[Chunk]:
        """
        Split text into chunks.

        Args:
            text: The full input text.
            config: Configuration parameters.

        Returns:
            A list of Chunk objects.
        """
        ...


@runtime_checkable
class Clusterer(Protocol):
    """Protocol for clustering engines."""

    def cluster_nodes(self, embeddings: list[list[float]], config: ProcessingConfig) -> list[Cluster]:
        """
        Cluster nodes based on embeddings.

        Args:
            embeddings: A list of vectors, where each vector corresponds to a node.
            config: Configuration parameters (e.g., n_clusters).

        Returns:
            A list of Cluster objects.
            The `node_indices` in each Cluster should correspond to the indices
            of the `embeddings` list provided as input.
        """
        ...


@runtime_checkable
class Summarizer(Protocol):
    """Protocol for summarization engines."""

    def summarize(self, text: str, config: ProcessingConfig) -> str:
        """
        Summarize the provided text.

        Args:
            text: The text to summarize.
            config: Configuration parameters (e.g., model name, max_tokens).

        Returns:
            The summary text.
        """
        ...
