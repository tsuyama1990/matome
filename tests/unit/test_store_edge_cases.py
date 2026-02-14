import json
import threading
import time
from pathlib import Path

import pytest
from sqlalchemy import text

from domain_models.manifest import Chunk
from matome.utils.store import DiskChunkStore, StoreError


def test_invalid_node_id_validation() -> None:
    """Test that invalid node IDs raise ValueError."""
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

    store.close()


def test_large_batch_processing(tmp_path: Path) -> None:
    """Test processing a batch larger than the internal read buffer."""
    store = DiskChunkStore(tmp_path / "large_batch.db", read_batch_size=10)

    # Create 25 chunks (2.5 batches)
    chunks = [
        Chunk(index=i, text=f"C{i}", start_char_idx=0, end_char_idx=1)
        for i in range(25)
    ]
    store.add_chunks(chunks)

    # Retrieve all 25
    ids = [str(i) for i in range(25)]
    retrieved = list(store.get_nodes(ids))

    assert len(retrieved) == 25
    assert all(n is not None for n in retrieved)

    # Check typing (mypy requires isinstance check or cast if we access attrs on Union)
    first = retrieved[0]
    assert isinstance(first, Chunk)
    assert first.index == 0

    last = retrieved[24]
    assert isinstance(last, Chunk)
    assert last.index == 24

    store.close()


def test_corruption_prevention(tmp_path: Path) -> None:
    """Test that the database (via index) prevents corrupted JSON data."""
    store = DiskChunkStore(tmp_path / "corrupt.db")

    # Attempt to manually insert corrupted data should fail due to JSON index
    # Exception type is usually OperationalError wrapped or raw
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
        for i in range(50):
            if stop_event.is_set():
                break
            try:
                c = Chunk(index=0, text=f"Update {i}", start_char_idx=0, end_char_idx=1)
                # This uses transaction internally
                store.add_chunk(c)
                time.sleep(0.001)
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
    store.close()
