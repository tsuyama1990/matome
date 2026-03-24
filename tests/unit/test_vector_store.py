import pytest
from src.infrastructure.vector_store import InMemoryVectorStore


def test_vector_store_upsert_and_search() -> None:
    store = InMemoryVectorStore()
    records = [
        {"id": "1", "embedding": [1.0, 0.0, 0.0], "text": "A"},
        {"id": "2", "embedding": [0.0, 1.0, 0.0], "text": "B"},
        {"id": "3", "embedding": [0.0, 0.0, 1.0], "text": "C"},
    ]
    store.upsert("test_col", records)

    # Update
    records_update = [
        {"id": "2", "embedding": [0.0, 1.0, 0.0], "text": "B updated"},
        {"embedding": [1.0, 1.0, 1.0], "text": "no id"},
    ]
    store.upsert("test_col", records_update)

    results = store.search("test_col", [1.0, 0.0, 0.0], 2)
    assert len(results) == 2
    assert results[0]["id"] == "1"

    # Not exist col
    results_empty = store.search("not_exist", [1.0], 1)
    assert len(results_empty) == 0


def test_in_memory_vector_store_upsert_search() -> None:
    from src.infrastructure.vector_store import InMemoryVectorStore

    store = InMemoryVectorStore()

    # Invalid name
    import pytest

    with pytest.raises(ValueError, match="Invalid"):
        store.upsert("inv@lid", [{"id": "1", "embedding": [0.1, 0.2]}])

    store.upsert(
        "valid-name", [{"id": "1", "embedding": [1.0, 0.0]}, {"id": "2", "embedding": [0.0, 1.0]}]
    )

    # Overwrite
    store.upsert("valid-name", [{"id": "1", "embedding": [1.0, 1.0]}])

    # Search
    results = store.search("valid-name", [1.0, 0.0], 1)
    assert len(results) == 1
    assert results[0]["id"] == "1"


def test_pinecone_vector_store_initialization() -> None:
    from src.infrastructure.vector_store import PineconeVectorStore

    store = PineconeVectorStore(api_key="test", environment="us-east", index_name="idx")
    assert store.base_url == "https://idx-us-east.pinecone.io"

    # Invalid name
    import pytest

    with pytest.raises(ValueError, match="Invalid"):
        store.search("inv@lid", [0.1], 1)

    # Large vector
    with pytest.raises(ValueError, match="too large"):
        store.search("valid", [0.1] * 3073, 1)

    store.close()


def test_pinecone_vector_store_upsert_search_mocked() -> None:
    from unittest.mock import MagicMock

    import pytest

    from src.infrastructure.vector_store import PineconeVectorStore

    store = PineconeVectorStore(api_key="test", environment="us-east", index_name="idx")

    # Mock the client
    store.client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "matches": [
            {"id": "1", "score": 0.9, "metadata": {"foo": "bar"}},
            {"id": "2", "score": 0.8},
        ]
    }
    store.client.post.return_value = mock_response

    # test upsert
    store.upsert(
        "valid", [{"id": "1", "embedding": [0.1, 0.2], "meta": "data", "list": ["a", "b"]}]
    )
    store.client.post.assert_called_with(
        "/vectors/upsert",
        json={
            "vectors": [
                {"id": "1", "values": [0.1, 0.2], "metadata": {"meta": "data", "list": ["a", "b"]}}
            ],
            "namespace": "valid",
        },
    )

    # test search
    results = store.search("valid", [0.1, 0.2], 2)
    assert len(results) == 2
    assert results[0]["id"] == "1"
    assert results[0]["foo"] == "bar"

    # Test HTTP errors
    import httpx

    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with pytest.raises(RuntimeError, match="Failed"):
        store.upsert("valid", [{"id": "1", "embedding": [0.1]}])

    with pytest.raises(RuntimeError, match="Failed"):
        store.search("valid", [0.1], 1)

    # test validation inside upsert
    with pytest.raises(ValueError, match="missing required fields"):
        store.upsert("valid", [{"id": "1"}])  # missing embedding

@pytest.mark.asyncio
async def test_vector_db_adapter() -> None:
    from src.infrastructure.vector_store import VectorDBAdapter, InMemoryVectorStore
    from src.domain_models.document import SemanticChunk, ChunkMetadata
    import uuid

    in_memory = InMemoryVectorStore()
    adapter = VectorDBAdapter(vector_store=in_memory)

    chunk_id = uuid.uuid4()
    chunks = [
        SemanticChunk(
            id=chunk_id,
            content="test content",
            embedding=[0.1] * 384,
            metadata=ChunkMetadata(source_file="test.txt", time_axis="Past")
        )
    ]

    await adapter.upsert(chunks)

    results = await adapter.search([0.1] * 384, top_k=1)
    assert len(results) == 1
    assert results[0].id == chunk_id
    assert results[0].content == "test content"
