from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from domain_models.manifest import Chunk
from matome.utils.store import DiskChunkStore


def test_concurrent_writes(tmp_path: Path) -> None:
    """Verify that DiskChunkStore handles concurrent writes correctly."""
    db_path = tmp_path / "concurrent.db"
    store = DiskChunkStore(db_path=db_path)

    def write_chunks(start_idx: int, count: int) -> None:
        chunks = []
        for i in range(count):
            chunks.append(
                Chunk(
                    index=start_idx + i,
                    text=f"Chunk {start_idx + i}",
                    start_char_idx=0,
                    end_char_idx=10,
                    embedding=[0.1, 0.2],
                )
            )
        store.add_chunks(chunks)

    num_threads = 4
    chunks_per_thread = 25

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for i in range(num_threads):
            futures.append(executor.submit(write_chunks, i * chunks_per_thread, chunks_per_thread))

        for f in futures:
            f.result()  # Propagate exceptions

    # Verify total
    total_chunks = num_threads * chunks_per_thread

    # Check persistence
    missing = 0
    for i in range(total_chunks):
        if not store.get_node(i):
            missing += 1

    store.close()
    assert missing == 0, f"Missing {missing} chunks out of {total_chunks}"


def test_concurrent_read_write(tmp_path: Path) -> None:
    """Verify concurrent reads and writes."""
    db_path = tmp_path / "rw.db"
    store = DiskChunkStore(db_path=db_path)

    # Pre-populate some
    store.add_chunk(
        Chunk(index=999, text="Base", start_char_idx=0, end_char_idx=4, embedding=[0.0])
    )

    def writer() -> None:
        for i in range(50):
            store.add_chunk(
                Chunk(index=i, text=f"W{i}", start_char_idx=0, end_char_idx=1, embedding=[1.0])
            )

    def reader() -> None:
        for _ in range(50):
            store.get_node(999)  # Read base
            # Try to read something that might be written
            store.get_node(25)

    with ThreadPoolExecutor(max_workers=4) as executor:
        f1 = executor.submit(writer)
        f2 = executor.submit(reader)
        f3 = executor.submit(writer)  # Another writer

        f1.result()
        f2.result()
        f3.result()

    store.close()
