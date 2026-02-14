from collections.abc import Iterator

from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel

# Shared Test Utility for Chunk Generation
# This avoids DRY violations and ensures consistent test data generation.

def generate_chunks(count: int, start_index: int = 0) -> Iterator[Chunk]:
    """
    Generator for chunks to test streaming capabilities without memory overhead.
    """
    for i in range(count):
        yield Chunk(
            index=start_index + i,
            text=f"Chunk {start_index + i}",
            start_char_idx=0,
            end_char_idx=10,
            embedding=[0.1, 0.2]
        )

def generate_summary_node(
    node_id: str,
    level: int = 1,
    dikw_level: DIKWLevel = DIKWLevel.DATA
) -> SummaryNode:
    """Factory for creating SummaryNodes with consistent defaults."""
    return SummaryNode(
        id=node_id,
        text="Test Summary",
        level=level,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=dikw_level),
    )
