import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.utils.store import DiskChunkStore

# Constants
NUM_THREADS = 4
CHUNKS_PER_THREAD = 25
TOTAL_CHUNKS = NUM_THREADS * CHUNKS_PER_THREAD
READ_LOOPS = 10
WRITE_LOOPS = 10


def test_concurrent_writes(tmp_path: Path) -> None:
    """Verify that DiskChunkStore handles concurrent writes correctly using streaming."""
    db_path = tmp_path / "concurrent.db"
    store = DiskChunkStore(db_path=db_path)

    def chunk_generator(start_idx: int, count: int) -> Iterator[Chunk]:
        for i in range(count):
            yield Chunk(
                index=start_idx + i,
                text=f"Chunk {start_idx + i}",
                start_char_idx=0,
                end_char_idx=10,
                embedding=[0.1, 0.2],
            )

    def write_chunks(start_idx: int, count: int) -> None:
        # Use generator to stream chunks instead of loading all into list
        store.add_chunks(chunk_generator(start_idx, count))

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []
        for i in range(NUM_THREADS):
            futures.append(executor.submit(write_chunks, i * CHUNKS_PER_THREAD, CHUNKS_PER_THREAD))

        for f in futures:
            f.result()  # Propagate exceptions

    # Verify total using count query (O(1) instead of loop)
    count = store.get_node_count(0)  # Level 0 is chunks
    assert count == TOTAL_CHUNKS

    store.close()


def test_concurrent_read_write(tmp_path: Path) -> None:
    """Verify concurrent reads and writes."""
    db_path = tmp_path / "rw.db"
    store = DiskChunkStore(db_path=db_path)

    # Pre-populate some
    store.add_chunk(
        Chunk(index=999, text="Base", start_char_idx=0, end_char_idx=4, embedding=[0.0])
    )

    def writer() -> None:
        for i in range(WRITE_LOOPS):
            store.add_chunk(
                Chunk(index=i, text=f"W{i}", start_char_idx=0, end_char_idx=1, embedding=[1.0])
            )

    def reader() -> None:
        # Batch retrieval is more efficient than loop of single gets
        ids = ["999"] + [str(i) for i in range(5)]
        for _ in range(READ_LOOPS):
            list(store.get_nodes(ids))

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
    def read_loop() -> None:
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
    def write_loop() -> None:
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
    assert final_node is not None
    assert final_node.text.startswith("Update"), "Node was not updated."

    store.close()


def test_db_corruption_handling(tmp_path: Path) -> None:
    """Test handling of database errors during operations."""
    db_path = tmp_path / "corrupt.db"
    store = DiskChunkStore(db_path=db_path)

    # Mock execute to simulate a database error (e.g., malformed disk image)
    # We patch the engine's connect/begin to return a connection that fails on execute
    with patch.object(store.engine, 'connect') as mock_connect:
        mock_conn = mock_connect.return_value.__enter__.return_value
        mock_conn.execute.side_effect = OperationalError("disk I/O error", params=None, orig=Exception("Disk Error"))

        # Test get_node handles DB error by propagating it (standardized behavior)
        with pytest.raises(OperationalError, match="disk I/O error"):
            store.get_node(1)

    store.close()
