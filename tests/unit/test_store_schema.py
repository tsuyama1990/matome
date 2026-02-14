from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select

from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.utils.store import DiskChunkStore


def test_add_chunks_streaming(tmp_path: Path) -> None:
    """Test that add_chunks handles iterators and persists correctly."""
    store_path = tmp_path / "stream_store.db"
    store = DiskChunkStore(store_path)

    def chunk_generator() -> Iterator[Chunk]:
        for i in range(5):
            yield Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=5)

    store.add_chunks(chunk_generator())

    # Verify storage using safe query
    with store.engine.connect() as conn:
        stmt = select(func.count()).select_from(store.nodes_table).where(store.nodes_table.c.type == "chunk")
        result = conn.execute(stmt)
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

    # Check DB internals
    with store.engine.connect() as conn:
        stmt = select(store.nodes_table.c.embedding).where(store.nodes_table.c.id == "0")
        row = conn.execute(stmt).fetchone()
        assert row is not None
        assert "[0.1, 0.2, 0.3]" in row[0]  # Stored as JSON string

    store.close()


def test_chunk_with_embedding_roundtrip(tmp_path: Path) -> None:
    """Test that adding a chunk with embedding stores it correctly in separate column."""
    store_path = tmp_path / "rt_store.db"
    store = DiskChunkStore(store_path)

    chunk = Chunk(index=1, text="Test", start_char_idx=0, end_char_idx=4, embedding=[0.9, 0.9])
    store.add_chunk(chunk)

    fetched = store.get_node(1)
    assert fetched is not None
    assert fetched.embedding == [0.9, 0.9]

    # Verify separation in DB
    with store.engine.connect() as conn:
        stmt = select(store.nodes_table.c.content, store.nodes_table.c.embedding).where(store.nodes_table.c.id == "1")
        row = conn.execute(stmt).fetchone()
        assert row is not None
        content_json, embedding_json = row
        assert "embedding" not in content_json  # We excluded it
        assert embedding_json == "[0.9, 0.9]"

    store.close()


def test_update_node_persistence() -> None:
    """Test that update_node actually updates the record."""
    store = DiskChunkStore()
    node = SummaryNode(
        id="u1",
        text="Original",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.DATA),
    )
    store.add_summary(node)

    # Verify original
    fetched = store.get_node("u1")
    assert fetched is not None
    assert fetched.text == "Original"

    # Update
    node.text = "Updated"
    store.update_node(node)

    # Verify update
    fetched_updated = store.get_node("u1")
    assert fetched_updated is not None
    assert fetched_updated.text == "Updated"


def test_update_node_non_existent() -> None:
    """Test updating a non-existent node (should probably do nothing or fail silently with UPDATE)."""
    store = DiskChunkStore()
    node = SummaryNode(
        id="non_existent",
        text="Ghost",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.DATA),
    )

    # Should not raise error
    store.update_node(node)

    # Should not exist
    assert store.get_node("non_existent") is None


def test_update_node_with_embedding() -> None:
    """Test updating a node that has an embedding."""
    store = DiskChunkStore()
    node = SummaryNode(
        id="u_emb",
        text="Text",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.DATA),
        embedding=[0.1, 0.2]
    )
    store.add_summary(node)

    # Update embedding
    node.embedding = [0.3, 0.4]
    store.update_node(node)

    fetched = store.get_node("u_emb")
    assert fetched is not None
    assert fetched.embedding == [0.3, 0.4]


def test_transaction_rollback_on_error(tmp_path: Path) -> None:
    """Test that batch operations rollback on error."""
    store = DiskChunkStore(tmp_path / "rollback.db")
    chunks = [Chunk(index=i, text="C", start_char_idx=0, end_char_idx=1) for i in range(10)]

    class BrokenConnection:
        def __enter__(self) -> "BrokenConnection":
            return self

        def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
            pass

        def execute(self, stmt: object, params: object = None) -> None:
            msg = "Database exploded"
            raise RuntimeError(msg)

    # Patch the begin method of the engine instance on the store
    # Since store.engine is an instance attribute, we can patch it directly or use patch.object
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(store.engine, "begin", MagicMock(return_value=BrokenConnection()))

        with pytest.raises(RuntimeError, match="Database exploded"):
            store.add_chunks(chunks)

def test_empty_db_operations() -> None:
    """Test operations on an empty database."""
    store = DiskChunkStore()

    # Get non-existent node
    assert store.get_node("999") is None

    # Get multiple non-existent nodes
    nodes = list(store.get_nodes(["999", "888"]))
    assert nodes == [None, None]

    # Count should be 0
    assert store.get_node_count(0) == 0
    assert store.get_node_count(1) == 0

    # Streaming IDs should be empty
    assert list(store.get_node_ids_by_level(0)) == []

    store.close()
