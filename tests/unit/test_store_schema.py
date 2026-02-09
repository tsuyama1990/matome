from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import text

from domain_models.manifest import Chunk
from matome.utils.store import TABLE_NODES, DiskChunkStore


def test_add_chunks_streaming(tmp_path: Path) -> None:
    """Test that add_chunks handles iterators and persists correctly."""
    store_path = tmp_path / "stream_store.db"
    store = DiskChunkStore(store_path)

    def chunk_generator() -> Iterator[Chunk]:
        for i in range(5):
            yield Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=5)

    store.add_chunks(chunk_generator())

    # Verify storage
    with store.engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {TABLE_NODES} WHERE type=:type"), {"type": "chunk"}  # noqa: S608
        )
        assert result.scalar() == 5

    store.close()


def test_update_node_embedding_direct(tmp_path: Path) -> None:
    """Test updating embedding without fetching the node."""
    store_path = tmp_path / "embed_store.db"
    store = DiskChunkStore(store_path)

    # Add chunk without embedding
    chunk = Chunk(index=0, text="Test", start_char_idx=0, end_char_idx=4)
    store.add_chunk(chunk)

    # Update embedding
    embedding = [0.1, 0.2, 0.3]
    store.update_node_embedding(chunk.index, embedding)

    # Fetch and verify
    fetched = store.get_node(chunk.index)
    assert fetched is not None
    assert fetched.embedding == embedding

    # Verify content JSON didn't change (still lacks embedding if we stripped it, or has old one)
    # But get_node re-assembles it.

    # Check DB internals
    with store.engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT embedding FROM {TABLE_NODES} WHERE id=:id"), {"id": "0"}  # noqa: S608
        ).fetchone()
        assert row is not None
        assert "[0.1, 0.2, 0.3]" in row[0]  # Stored as JSON string

    store.close()


def test_chunk_with_embedding_roundtrip(tmp_path: Path) -> None:
    """Test that adding a chunk with embedding stores it correctly in separate column."""
    store_path = tmp_path / "rt_store.db"
    store = DiskChunkStore(store_path)

    chunk = Chunk(
        index=1, text="Test", start_char_idx=0, end_char_idx=4, embedding=[0.9, 0.9]
    )
    store.add_chunk(chunk)

    fetched = store.get_node(1)
    assert fetched is not None
    assert fetched.embedding == [0.9, 0.9]

    # Verify separation in DB
    with store.engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT content, embedding FROM {TABLE_NODES} WHERE id=:id"), {"id": "1"}  # noqa: S608
        ).fetchone()
        assert row is not None
        content_json, embedding_json = row
        assert "embedding" not in content_json  # We excluded it
        assert embedding_json == "[0.9, 0.9]"

    store.close()
