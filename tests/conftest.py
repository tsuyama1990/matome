from collections.abc import Iterator

from domain_models.manifest import Chunk

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
