from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ClusteringStrategy(Protocol):
    """Protocol for embedding clustering strategies."""

    def reduce_dimensions(self, embeddings: list[list[float]]) -> Any: ...
    def cluster(self, embeddings: Any, max_clusters: int) -> dict[int, list[int]]: ...
