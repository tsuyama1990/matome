import concurrent.futures
from pathlib import Path

from domain_models.manifest import Chunk
from matome.utils.store import DiskChunkStore


def test_store_concurrent_writes(tmp_path: Path) -> None:
    """
    Test that multiple threads can write to the store concurrently without locking errors.
    This verifies that the DiskChunkStore correctly handles SQLite concurrency (WAL mode, timeouts).
    """
    db_path = tmp_path / "concurrent_store.db"

    # Initialize store (creates tables)
    with DiskChunkStore(db_path):
        pass

    # Number of threads and operations
    num_threads = 5
    ops_per_thread = 50

    # We use a shared store instance to test if its methods are thread-safe
    # (i.e., they open/close connections properly per call)
    # Note: If DiskChunkStore holds a single connection, this will fail.
    # It must use per-call connections or a pool.
    store = DiskChunkStore(db_path)

    def writer_task(thread_id: int) -> None:
        for i in range(ops_per_thread):
            chunk_idx = thread_id * 1000 + i
            chunk = Chunk(
                index=chunk_idx,
                text=f"Thread {thread_id} Chunk {i}",
                start_char_idx=0,
                end_char_idx=10,
                embedding=[0.1] * 10,  # Mock embedding
            )
            store.add_chunk(chunk)

            # Simulate read-after-write
            if i > 0:
                prev_idx = thread_id * 1000 + (i - 1)
                node = store.get_node(prev_idx)
                assert node is not None
                assert node.text == f"Thread {thread_id} Chunk {i - 1}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(writer_task, i) for i in range(num_threads)]

        for future in concurrent.futures.as_completed(futures):
            future.result()  # Raises exception if thread failed

    store.close()

    # Verify persistence with a fresh store instance
    with DiskChunkStore(db_path) as final_store:
        for t in range(num_threads):
            for i in range(ops_per_thread):
                idx = t * 1000 + i
                node = final_store.get_node(idx)
                assert node is not None
                assert node.text == f"Thread {t} Chunk {i}"
