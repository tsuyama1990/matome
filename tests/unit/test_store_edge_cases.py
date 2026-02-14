import json
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from domain_models.manifest import Chunk
from matome.utils.store import DiskChunkStore, StoreError
from tests.conftest import generate_chunks


def test_invalid_node_id_validation() -> None:
    """Test that invalid node IDs raise ValueError, including path traversal."""
    store = DiskChunkStore()

    # Valid IDs
    store.get_node("valid_id_1")
    store.get_node("123")
    store.get_node("node-1")

    # Invalid IDs (SQL injection attempts or bad chars)
    with pytest.raises(ValueError, match="Invalid node ID format"):
        store.get_node("id; DROP TABLE nodes")

    with pytest.raises(ValueError, match="Invalid node ID format"):
        store.get_node("id with spaces")

    # Path Traversal Check
    with pytest.raises(ValueError, match="Invalid node ID format"):
        store.get_node("../../../etc/passwd")

    store.close()


def test_large_batch_processing(tmp_path: Path) -> None:
    """Test processing a batch larger than the internal read buffer using streaming."""
    store = DiskChunkStore(tmp_path / "large_batch.db", read_batch_size=10)

    # Stream chunks directly (no list comprehension)
    store.add_chunks(generate_chunks(25))

    # Retrieve all 25
    ids = [str(i) for i in range(25)]

    # Use streaming iteration instead of loading entire list into memory
    # We verify count and type on the fly
    count = 0
    first_node = None
    last_node = None

    for node in store.get_nodes(ids):
        assert node is not None
        if count == 0:
            first_node = node
        last_node = node
        count += 1

    assert count == 25

    # Check typing (mypy requires isinstance check or cast if we access attrs on Union)
    assert isinstance(first_node, Chunk)
    assert first_node.index == 0

    assert isinstance(last_node, Chunk)
    assert last_node.index == 24

    store.close()


def test_corruption_prevention(tmp_path: Path) -> None:
    """Test that the database (via index) prevents corrupted JSON data."""
    store = DiskChunkStore(tmp_path / "corrupt.db")

    # Attempt to manually insert corrupted data should fail due to JSON index
    # We use parameterized query to ensure the test itself is safe from injection
    with (
        pytest.raises(Exception, match="malformed JSON"),
        store.engine.begin() as conn,
    ):
        conn.execute(
            text("INSERT INTO nodes (id, type, content, embedding) VALUES (:id, :type, :content, :emb)"),
            {"id": "bad1", "type": "chunk", "content": "{bad_json", "emb": None}
        )

    store.close()


def test_transaction_rollback_explicit(tmp_path: Path) -> None:
    """Test that transactions roll back changes on error."""
    store = DiskChunkStore(tmp_path / "rollback.db")

    chunk = Chunk(index=1, text="Original", start_char_idx=0, end_char_idx=5)
    store.add_chunk(chunk)

    def raise_boom() -> None:
        msg = "Boom"
        raise RuntimeError(msg)

    try:
        with store.transaction() as conn:
            # Update via raw SQL with VALID JSON (so DB doesn't complain)
            valid_json = json.dumps({"text": "Modified", "metadata": {}, "level": 1})
            conn.execute(
                text("UPDATE nodes SET content = :content WHERE id = :id"),
                {"content": valid_json, "id": "1"}
            )
            # Raise error to trigger rollback
            raise_boom()
    except RuntimeError:
        pass
    except StoreError:
        # Our wrapper catches it
        # Assert within exception context
        pass

    # Verify rollback
    # Should be original JSON
    node = store.get_node("1")
    # node can be Chunk | SummaryNode | None
    assert isinstance(node, Chunk)
    assert node.text == "Original"

    store.close()


def test_concurrent_read_write(tmp_path: Path) -> None:
    """Stress test concurrent reads and writes."""
    store = DiskChunkStore(tmp_path / "concurrency.db")

    # Initialize
    store.add_chunk(Chunk(index=0, text="Init", start_char_idx=0, end_char_idx=1))

    stop_event = threading.Event()
    errors = []

    def writer() -> None:
        # Batch write operations to improve I/O efficiency and avoid tight loops
        # We will do 5 batches of 10 updates each
        for i in range(5):
            if stop_event.is_set():
                break
            try:
                # Create batch of chunks (same ID being updated, effectively simulates intense updates)
                # But to really test batching we should probably insert unique ones or update in batch.
                # Since update_node is single-item, let's use add_chunks which is batched.
                # We will update the SAME chunk multiple times in a batch? No, DB constraints.
                # So we update it once per batch iteration.
                c = Chunk(index=0, text=f"Update {i}", start_char_idx=0, end_char_idx=1)
                # add_chunks uses "OR REPLACE", so this is a valid update.
                store.add_chunks([c])
                time.sleep(0.005)
            except Exception as e:
                errors.append(f"Writer failed: {e}")

    def reader() -> None:
        for _ in range(50):
            if stop_event.is_set():
                break
            try:
                n = store.get_node("0")
                if not n:
                    errors.append("Node 0 vanished")
                time.sleep(0.001)
            except Exception as e:
                errors.append(f"Reader failed: {e}")

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    assert not errors, f"Concurrency errors: {errors}"

    # Final Consistency Check
    final_node = store.get_node("0")
    assert final_node is not None
    # Depending on race, it will be one of the updates or init, but valid.
    assert isinstance(final_node, Chunk)
    assert final_node.text.startswith("Update") or final_node.text == "Init"

    store.close()

def test_streaming_connection_failure(tmp_path: Path) -> None:
    """Test that streaming handles connection failures during iteration."""
    store = DiskChunkStore(tmp_path / "streaming_fail.db")
    store.add_chunk(Chunk(index=1, text="C1", start_char_idx=0, end_char_idx=1))

    # We patch execute to simulate a DB failure during streaming
    with patch.object(store.engine, 'connect') as mock_connect:
        mock_conn = mock_connect.return_value.__enter__.return_value
        # Use Exception instead of None for orig to satisfy typing
        mock_conn.execute.side_effect = OperationalError("Lost connection", params=None, orig=Exception("Lost"))

        with pytest.raises(StoreError, match="Failed to retrieve nodes batch"):
            list(store.get_nodes(["1"]))

    store.close()
