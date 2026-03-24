from typing import Any, Protocol, runtime_checkable

from src.domain_models import SemanticChunk


@runtime_checkable
class ClusteringStrategy(Protocol):
    """Protocol for embedding clustering strategies."""

    def reduce_dimensions(self, embeddings: list[list[float]]) -> Any: ...
    def cluster(self, embeddings: Any, max_clusters: int) -> dict[int, list[int]]: ...


@runtime_checkable
class PivotEngineProtocol(Protocol):
    """Protocol for orchestrating dynamic re-clustering of semantic chunks."""

    def pivot(self, chunks: list[SemanticChunk], axis: str) -> dict[str, list[SemanticChunk]]: ...
