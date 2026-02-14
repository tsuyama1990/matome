import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
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

def test_store_concurrency_stress(tmp_path: Path) -> None:
    """
    Integration test for DiskChunkStore concurrency using actual file on disk.
    Verifies WAL mode effectiveness.
    """
    db_path = tmp_path / "concurrent_stress.db"
    store = DiskChunkStore(db_path=db_path)

    # Setup initial state
    node_id = "stress_node"
    node = SummaryNode(
        id=node_id,
        text="Start",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.DATA),
    )
    store.add_summary(node)

    stop_event = threading.Event()
    exceptions = []

    # Reader Thread
    def read_loop():
        # Open a separate store instance to simulate separate connection/process
        reader_store = DiskChunkStore(db_path=db_path)
        while not stop_event.is_set():
            try:
                n = reader_store.get_node(node_id)
                if n is None:
                    exceptions.append("Node missing!")
            except Exception as e:
                exceptions.append(f"Read Error: {e}")
            time.sleep(0.001)
        reader_store.close()

    # Writer Thread
    def write_loop():
        writer_store = DiskChunkStore(db_path=db_path)
        count = 0
        while not stop_event.is_set():
            try:
                n = SummaryNode(
                    id=node_id,
                    text=f"Update {count}",
                    level=1,
                    children_indices=[],
                    metadata=NodeMetadata(dikw_level=DIKWLevel.DATA),
                )
                writer_store.update_node(n)
                count += 1
            except Exception as e:
                exceptions.append(f"Write Error: {e}")
            time.sleep(0.002)
        writer_store.close()

    t_read = threading.Thread(target=read_loop)
    t_write = threading.Thread(target=write_loop)

    t_read.start()
    t_write.start()

    time.sleep(1.0)
    stop_event.set()

    t_read.join()
    t_write.join()

    assert not exceptions, f"Exceptions encountered: {exceptions}"

    # Verify final state
    final_node = store.get_node(node_id)
    assert final_node.text.startswith("Update"), "Node was not updated."

    store.close()
