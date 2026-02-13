from collections.abc import Iterator
from pathlib import Path

from domain_models.data_schema import NodeMetadata
from domain_models.constants import TABLE_NODES
from domain_models.manifest import Chunk, SummaryNode
from matome.utils.store import DiskChunkStore, get_db_connection


def test_add_chunks_streaming(tmp_path: Path) -> None:
    """Test that add_chunks handles iterators and persists correctly."""
    store_path = tmp_path / "stream_store.db"
    store = DiskChunkStore(store_path)

    def chunk_generator() -> Iterator[Chunk]:
        for i in range(5):
            yield Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=5)

    store.add_chunks(chunk_generator())

    # Verify storage
    with get_db_connection(store_path) as conn:
        cursor = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE_NODES} WHERE type=?",  # noqa: S608
            ("chunk",),
        )
        assert cursor.fetchone()[0] == 5

    store.close()


def test_update_node_embedding_direct(tmp_path: Path) -> None:
    """Test updating embedding without fetching the node."""
    store_path = tmp_path / "embed_store.db"
    # We must ensure store is initialized (tables created)
    with DiskChunkStore(store_path) as store:
        # Add chunk without embedding
        chunk = Chunk(index=0, text="Test", start_char_idx=0, end_char_idx=4)
        store.add_chunk(chunk)

    # Re-open or use helper to update (DiskChunkStore methods work on path)
    # The test intent is to use store instance.
    store = DiskChunkStore(store_path)

    # Update embedding
    embedding = [0.1, 0.2, 0.3]
    store.update_node_embedding(0, embedding)

    # Fetch and verify
    fetched = store.get_node(0)
    assert fetched is not None
    assert fetched.embedding == embedding

    # Check DB internals
    with get_db_connection(store_path) as conn:
        row = conn.execute(
            f"SELECT embedding FROM {TABLE_NODES} WHERE id=?",  # noqa: S608
            ("0",),
        ).fetchone()
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
    with get_db_connection(store_path) as conn:
        row = conn.execute(
            f"SELECT content, embedding FROM {TABLE_NODES} WHERE id=?",  # noqa: S608
            ("1",),
        ).fetchone()
        assert row is not None
        content_json, embedding_json = row
        assert "embedding" not in content_json  # We excluded it
        assert embedding_json == "[0.9, 0.9]"

    store.close()


def test_bulk_operations(tmp_path: Path) -> None:
    """Test get_nodes and update_embeddings."""
    store_path = tmp_path / "bulk_store.db"
    store = DiskChunkStore(store_path)

    # 1. Add Chunks
    chunks = [
        Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=5, embedding=[0.1, 0.1])
        for i in range(10)
    ]
    store.add_chunks(chunks)

    # 2. Add Summaries
    summaries = [
        SummaryNode(
            id=f"summary_{i}",
            text=f"Summary {i}",
            level=1,
            children_indices=[],
            metadata=NodeMetadata(),
        )
        for i in range(5)
    ]
    store.add_summaries(summaries)

    # 3. Test get_nodes (mixed types)
    ids_to_fetch: list[int | str] = [0, 1, "summary_0", "summary_1", 999]  # 999 is missing
    # ids_to_fetch has mixed int and str, plus potentially an int ID that doesn't exist
    # get_nodes signature expects list[int | str] which is valid.
    nodes = store.get_nodes(ids_to_fetch)

    assert len(nodes) == 5
    assert isinstance(nodes[0], Chunk)
    assert nodes[0].index == 0
    assert isinstance(nodes[1], Chunk)
    assert isinstance(nodes["summary_0"], SummaryNode)
    assert isinstance(nodes["summary_1"], SummaryNode)
    assert nodes[999] is None

    # Test int vs str ID for chunks
    # This tests the "map back" logic in get_nodes
    nodes_str = store.get_nodes(["0", 1])
    node_0 = nodes_str["0"]
    node_1 = nodes_str[1]
    assert isinstance(node_0, Chunk)
    assert node_0.index == 0
    assert isinstance(node_1, Chunk)
    assert node_1.index == 1

    # 4. Test update_embeddings
    updates: list[tuple[int | str, list[float]]] = [(0, [0.9, 0.9]), ("summary_0", [0.8, 0.8])]
    store.update_embeddings(updates)

    # Verify updates
    updated_nodes = store.get_nodes([0, "summary_0"])
    u_node_0 = updated_nodes[0]
    u_node_s0 = updated_nodes["summary_0"]
    assert u_node_0 is not None
    assert u_node_0.embedding == [0.9, 0.9]
    assert u_node_s0 is not None
    assert u_node_s0.embedding == [0.8, 0.8]

    # Verify others untouched
    untouched = store.get_nodes([1])
    u_node_1 = untouched[1]
    assert u_node_1 is not None
    assert u_node_1.embedding == [0.1, 0.1]

    store.close()
