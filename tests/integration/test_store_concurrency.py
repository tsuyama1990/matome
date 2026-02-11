from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from domain_models.manifest import Chunk
from matome.utils.store import DiskChunkStore


def test_store_concurrency(tmp_path: Path) -> None:
    db_path = tmp_path / "test_concurrency.db"
    store = DiskChunkStore(db_path)

    # Write from multiple threads
    def write_chunk(i: int) -> None:
        chunk = Chunk(
            index=i,
            text=f"Chunk {i}",
            start_char_idx=i*10,
            end_char_idx=(i+1)*10,
            embedding=[0.1] * 128
        )
        # Each thread gets its own store instance or shares?
        # Sharing store instance across threads needs thread-safety.
        # SQLAlchemy engine is thread-safe.
        store.add_chunk(chunk)

    num_chunks = 50
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(write_chunk, i) for i in range(num_chunks)]
        for f in futures:
            f.result() # Propagate exceptions

    # Read back
    for i in range(num_chunks):
        node = store.get_node(i)
        assert node is not None
        assert isinstance(node, Chunk)
        assert node.index == i
