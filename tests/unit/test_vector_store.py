from src.infrastructure.vector_store import InMemoryVectorStore


def test_vector_store_upsert_and_search() -> None:
    store = InMemoryVectorStore()
    records = [
        {"id": "1", "embedding": [1.0, 0.0, 0.0], "text": "A"},
        {"id": "2", "embedding": [0.0, 1.0, 0.0], "text": "B"},
        {"id": "3", "embedding": [0.0, 0.0, 1.0], "text": "C"},
    ]
    store.upsert("test-col", records)

    # Update
    records_update = [
        {"id": "2", "embedding": [0.0, 1.0, 0.0], "text": "B updated"},
        {"embedding": [1.0, 1.0, 1.0], "text": "no id"}
    ]
    store.upsert("test-col", records_update)

    results = store.search("test-col", [1.0, 0.0, 0.0], 2)
    assert len(results) == 2
    assert results[0]["id"] == "1"

    # Not exist col
    results_empty = store.search("not-exist", [1.0], 1)
    assert len(results_empty) == 0
