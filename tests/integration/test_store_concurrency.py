import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from domain_models.manifest import Chunk
from domain_models.types import DIKWLevel
from matome.utils.store import DiskChunkStore, StoreError
from tests.conftest import generate_chunks, generate_summary_node
from tests.test_config import TEST_CONFIG


def test_concurrent_writes(tmp_path: Path) -> None:
    """Verify that DiskChunkStore handles concurrent writes correctly using streaming."""
    db_path = tmp_path / "concurrent.db"
    store = DiskChunkStore(db_path=db_path)

    def write_chunks(start_idx: int, count: int) -> None:
        # Use shared utility generator to stream chunks directly
        store.add_chunks(generate_chunks(count, start_index=start_idx))

    with ThreadPoolExecutor(max_workers=TEST_CONFIG.NUM_THREADS) as executor:
        futures = []
        for i in range(TEST_CONFIG.NUM_THREADS):
            futures.append(executor.submit(
                write_chunks,
                i * TEST_CONFIG.CHUNKS_PER_THREAD,
                TEST_CONFIG.CHUNKS_PER_THREAD
            ))

        for f in futures:
            f.result()  # Propagate exceptions

    # Verify total using count query (O(1) instead of loop)
    count = store.get_node_count(0)  # Level 0 is chunks
    assert count == TEST_CONFIG.total_chunks

    store.close()


def test_concurrent_read_write(tmp_path: Path) -> None:
    """Verify concurrent reads and writes with data consistency checks."""
    db_path = tmp_path / "rw.db"
    store = DiskChunkStore(db_path=db_path)

    # Pre-populate some
    store.add_chunk(
        Chunk(index=999, text="Base", start_char_idx=0, end_char_idx=4, embedding=[0.0])
    )

    def writer() -> None:
        # Stream chunks using generator instead of list comprehension
        def chunk_gen() -> Iterator[Chunk]:
            for i in range(TEST_CONFIG.WRITE_LOOPS):
                yield Chunk(
                    index=i,
                    text=f"W{i}",
                    start_char_idx=0,
                    end_char_idx=1,
                    embedding=[1.0]
                )

        store.add_chunks(chunk_gen())

    def reader() -> None:
        # Batch retrieval via iterator consumption
        ids = ["999"] + [str(i) for i in range(5)]

        for _ in range(TEST_CONFIG.READ_LOOPS):
            # Consume generator and verify "Base" exists
            found_base = False
            for node in store.get_nodes(ids):
                if node and isinstance(node, Chunk) and node.index == 999:
                    found_base = True

            # Simple consistency check within the loop
            if not found_base:
                msg = "Base node 999 vanished during concurrent read"
                raise RuntimeError(msg)

    with ThreadPoolExecutor(max_workers=4) as executor:
        f1 = executor.submit(writer)
        f2 = executor.submit(reader)
        f3 = executor.submit(writer)  # Another writer

        f1.result()
        f2.result()
        f3.result()

    # Final consistency verification
    base_node = store.get_node(999)
    assert base_node is not None
    assert base_node.text == "Base"

    # Check if writes persisted
    written_node = store.get_node(0)
    assert written_node is not None
    assert written_node.text == "W0"

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
    node = generate_summary_node(node_id, level=1, dikw_level=DIKWLevel.DATA)
    node.text = "Start"
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
                n = generate_summary_node(node_id, level=1, dikw_level=DIKWLevel.DATA)
                n.text = f"Update {count}"
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
    with patch.object(store.engine, 'connect') as mock_connect:
        mock_conn = mock_connect.return_value.__enter__.return_value
        # OperationalError requires params (None is acceptable) and orig (exception object)
        mock_conn.execute.side_effect = OperationalError("disk I/O error", params=None, orig=Exception("Disk Error"))

        # Test get_node handles DB error by propagating it (standardized behavior)
        with pytest.raises(StoreError, match="disk I/O error"):
            store.get_node(1)

    # Ensure cleanup is called/safe even after error
    # We can't assert 'close' was called internally unless we spy on it,
    # but we can call it and ensure no exception.
    try:
        store.close()
    except Exception as e:
        pytest.fail(f"store.close() raised exception: {e}")
