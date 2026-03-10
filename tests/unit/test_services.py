import pytest

from src.infrastructure.services import (
    DefaultClusteringService,
    DefaultEntityExtractor,
    DefaultTextSplitter,
    RequestsHTTPClient,
    TenacityRetryPolicy,
)


def test_default_text_splitter_split_text() -> None:
    splitter = DefaultTextSplitter(chunk_size=10, chunk_overlap=2, max_file_size=1000)
    text = "01234567890123456789"
    chunks = splitter.split_text(text)
    assert len(chunks) > 0


def test_default_text_splitter_empty() -> None:
    splitter = DefaultTextSplitter(chunk_size=10, chunk_overlap=2, max_file_size=1000)
    with pytest.raises(ValueError, match="Semantic chunking returned no content"):
        splitter.split_text("")


def test_default_text_splitter_split_document(tmp_path: pytest.TempPathFactory) -> None:
    splitter = DefaultTextSplitter(chunk_size=10, chunk_overlap=2, max_file_size=500000)
    file_path = tmp_path / "test.txt"  # type: ignore[operator]
    file_path.write_text("01234567890123456789" * 1000)

    iterator = splitter.split_document(str(file_path))
    chunks = list(iterator)
    assert len(chunks) > 0


def test_default_text_splitter_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    # Force LangChain import to fail
    monkeypatch.setitem(sys.modules, "langchain_text_splitters", None)

    splitter = DefaultTextSplitter(chunk_size=10, chunk_overlap=2, max_file_size=1000)
    text = "01234567890123456789"
    chunks = splitter.split_text(text)

    assert chunks[0] == "0123456789"
    assert chunks[1] == "8901234567"


def test_default_entity_extractor_fallback() -> None:
    extractor = DefaultEntityExtractor(spacy_model="invalid_model_name")
    chunks = iter(["Test Chunk", "Another Chunk with Entities"])

    entities = extractor.extract_entities(chunks)
    assert isinstance(entities, dict)
    assert len(entities) > 0
    # Verify fallback regex behavior caught capital words
    assert "chunk_0_Fallback_ORG" in entities
    assert entities["chunk_0_Fallback_ORG"] == "Test Chunk"


def test_default_entity_extractor_missing_spacy(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "spacy", None)

    extractor = DefaultEntityExtractor(spacy_model="en_core_web_sm")
    chunks = iter(["Test Chunk", "Another Chunk with Entities"])

    entities = extractor.extract_entities(chunks)
    assert isinstance(entities, dict)
    # Verify fallback logic executes correctly when spacy is entirely missing
    assert "chunk_0_Fallback_ORG" in entities


def test_default_clustering_service_not_enough_chunks() -> None:
    clustering_service = DefaultClusteringService(random_seed=42)
    chunks = iter(["chunk 1", "chunk 2"])

    result = clustering_service.cluster_chunks(chunks, max_clusters=5)
    assert result["clusters_found"] == "1 (not enough chunks for clustering)"


def test_default_clustering_service_invalid_max_clusters() -> None:
    clustering_service = DefaultClusteringService(random_seed=42)
    with pytest.raises(ValueError, match="must be at least 1"):
        clustering_service.cluster_chunks(["chunk 1"], max_clusters=0)


def test_default_clustering_service_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "sklearn.cluster", None)

    clustering_service = DefaultClusteringService(random_seed=42)
    chunks = iter([f"chunk {i}" for i in range(20)])

    result = clustering_service.cluster_chunks(chunks, max_clusters=5)
    assert result["algorithm"] == "None (Missing ML modules)"


def test_requests_http_client_post(monkeypatch: pytest.MonkeyPatch) -> None:
    import typing

    import requests

    class MockResponse:
        def __init__(self, json_data: dict[str, typing.Any], status_code: int = 200) -> None:
            self.json_data = json_data
            self.status_code = status_code

        def json(self) -> dict[str, typing.Any]:
            return self.json_data

        def raise_for_status(self) -> None:
            pass

    def mock_post(*args: typing.Any, **kwargs: typing.Any) -> MockResponse:
        return MockResponse({"test": "data"})

    monkeypatch.setattr(requests, "post", mock_post)

    client = RequestsHTTPClient()
    result = client.post("http://test.com", {"key": "value"}, {"Authorization": "token"}, 10)
    assert result == {"test": "data"}


def test_requests_http_client_post_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import typing

    import requests

    from src.domain_models.exceptions import AIServiceError

    def mock_post(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        msg = "Mock timeout"
        raise requests.Timeout(msg)

    monkeypatch.setattr(requests, "post", mock_post)

    client = RequestsHTTPClient()
    with pytest.raises(AIServiceError, match="timed out"):
        client.post("http://test.com", {"key": "value"}, {"Authorization": "token"}, 10)


def test_requests_http_client_post_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import typing

    import requests

    from src.domain_models.exceptions import AIServiceError

    def mock_post(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        msg = "Mock error"
        raise requests.HTTPError(msg)

    monkeypatch.setattr(requests, "post", mock_post)

    client = RequestsHTTPClient()
    with pytest.raises(AIServiceError, match="HTTP error"):
        client.post("http://test.com", {"key": "value"}, {"Authorization": "token"}, 10)


def test_tenacity_retry_policy() -> None:
    policy = TenacityRetryPolicy(ai_retry_attempts=3, ai_retry_min_wait=1, ai_retry_max_wait=2)

    attempts = 0

    def mock_func() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            msg = "Mock error"
            raise ValueError(msg)
        return "success"

    result = policy.execute(mock_func)
    assert result == "success"
    assert attempts == 2
