from typing import Any, Protocol


class ClusteringStrategy(Protocol):
    """Protocol for embedding clustering strategies."""

    def reduce_dimensions(self, embeddings: list[list[float]]) -> Any: ...
    def cluster(self, embeddings: Any, max_clusters: int) -> dict[int, list[int]]: ...
