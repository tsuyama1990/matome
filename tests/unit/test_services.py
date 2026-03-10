from pathlib import Path

import pytest

from src.infrastructure.services import (
    DefaultClusteringService,
    DefaultTextSplitter,
    RequestsHTTPClient,
    TenacityRetryPolicy,
)


def test_default_text_splitter_split_text() -> None:
    from src.infrastructure.services import LangChainSplitterStrategy

    splitter = DefaultTextSplitter(
        chunk_size=10, chunk_overlap=2, max_file_size=1000, strategy=LangChainSplitterStrategy()
    )
    text = "01234567890123456789"
    chunks = splitter.split_text(text)
    assert len(chunks) > 0


def test_default_text_splitter_empty() -> None:
    from src.infrastructure.services import LangChainSplitterStrategy

    splitter = DefaultTextSplitter(
        chunk_size=10, chunk_overlap=2, max_file_size=1000, strategy=LangChainSplitterStrategy()
    )
    with pytest.raises(ValueError, match="Semantic chunking returned no content"):
        splitter.split_text("")


def test_default_text_splitter_split_document(tmp_path: Path) -> None:
    from src.infrastructure.services import LangChainSplitterStrategy

    splitter = DefaultTextSplitter(
        chunk_size=10, chunk_overlap=2, max_file_size=500000, strategy=LangChainSplitterStrategy()
    )
    file_path = tmp_path / "test.txt"
    file_path.write_text("01234567890123456789" * 1000)

    iterator = splitter.split_document(str(file_path))
    chunks = list(iterator)
    assert len(chunks) > 0


def test_default_text_splitter_split_document_exceeds_max_size(
    tmp_path: Path,
) -> None:
    from src.infrastructure.services import LangChainSplitterStrategy

    splitter = DefaultTextSplitter(
        chunk_size=10, chunk_overlap=2, max_file_size=50, strategy=LangChainSplitterStrategy()
    )
    file_path = tmp_path / "test_exceed.txt"
    file_path.write_text("01234567890123456789" * 10)

    iterator = splitter.split_document(str(file_path))
    with pytest.raises(
        ValueError, match="Security Error: File processing stream exceeded maximum allowed size"
    ):
        list(iterator)


def test_default_text_splitter_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    # Force LangChain import to fail
    monkeypatch.setitem(sys.modules, "langchain_text_splitters", None)

    from src.infrastructure.services import LangChainSplitterStrategy

    splitter = DefaultTextSplitter(
        chunk_size=10, chunk_overlap=2, max_file_size=1000, strategy=LangChainSplitterStrategy()
    )
    text = "01234567890123456789"
    chunks = splitter.split_text(text)

    assert chunks[0] == "0123456789"
    assert chunks[1] == "8901234567"


def test_default_entity_extractor_fallback() -> None:
    from src.infrastructure.services import (
        DefaultModelVerifier,
        EntityExtractorBuilder,
        EntityExtractorBuilderConfig,
    )
    from src.utils.rate_limit import RateLimiter

    builder_config = EntityExtractorBuilderConfig(
        spacy_model="invalid_model_name",
        trusted_models=["invalid_model_name"],
        trusted_hashes={},
        fallback_ner_regex=r"\b[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,3}\b",
        max_model_signature_size=1024,
    )
    extractor = EntityExtractorBuilder.build(
        builder_config=builder_config,
        rate_limiter=RateLimiter(0.01),
        model_verifier=DefaultModelVerifier({"invalid_model_name"}, {}, 1024),
    )
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

    from src.infrastructure.services import (
        DefaultModelVerifier,
        EntityExtractorBuilder,
        EntityExtractorBuilderConfig,
    )
    from src.utils.rate_limit import RateLimiter

    builder_config = EntityExtractorBuilderConfig(
        spacy_model="en_core_web_sm",
        trusted_models=["en_core_web_sm"],
        trusted_hashes={},
        fallback_ner_regex=r"\b[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,3}\b",
        max_model_signature_size=1024,
    )
    extractor = EntityExtractorBuilder.build(
        builder_config=builder_config,
        rate_limiter=RateLimiter(0.01),
        model_verifier=DefaultModelVerifier({"en_core_web_sm"}, {}, 1024),
    )
    chunks = iter(["Test Chunk", "Another Chunk with Entities"])

    entities = extractor.extract_entities(chunks)
    assert isinstance(entities, dict)
    # Verify fallback logic executes correctly when spacy is entirely missing
    assert "chunk_0_Fallback_ORG" in entities


def test_default_entity_extractor_valid_spacy(monkeypatch: pytest.MonkeyPatch) -> None:
    # Need to bypass actual cryptographic signature check while validating spacy execution

    class MockSpacyNLPService:
        def extract_entities(self, text: str) -> list[tuple[str, str]]:
            return [("ORG", "MockCompany")]

    from src.infrastructure.services import (
        DefaultModelVerifier,
        EntityExtractorBuilder,
        EntityExtractorBuilderConfig,
    )
    from src.utils.rate_limit import RateLimiter

    builder_config = EntityExtractorBuilderConfig(
        spacy_model="test_model",
        trusted_models=["test_model"],
        trusted_hashes={},
        fallback_ner_regex=r"\b[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,3}\b",
        max_model_signature_size=1024,
    )
    verifier = DefaultModelVerifier({"test_model"}, {}, 1024)

    # Monkeypatch the signature check so it doesn't fail trying to read test_model
    def mock_verify(*args: object, **kwargs: object) -> None:
        pass

    monkeypatch.setattr(verifier, "verify_model_signature", mock_verify)

    extractor = EntityExtractorBuilder.build(
        builder_config=builder_config,
        rate_limiter=RateLimiter(0.01),
        model_verifier=verifier,
        nlp_service=MockSpacyNLPService(),
    )

    chunks = iter(["Test Chunk", "Another Chunk with Entities"])
    entities = extractor.extract_entities(chunks)
    assert isinstance(entities, dict)
    assert "chunk_0_ORG" in entities
    assert entities["chunk_0_ORG"] == "MockCompany"


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

    # Needs valid ca_bundle mock or file, bypass by monkeypatching Path.is_file

    monkeypatch.setattr(Path, "is_file", lambda self: True)

    result = client.post(
        "http://test.com", {"key": "value"}, {"Authorization": "token"}, 10, verify="mock_cert.pem"
    )
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


    monkeypatch.setattr(Path, "is_file", lambda self: True)

    with pytest.raises(AIServiceError, match="timed out"):
        client.post(
            "http://test.com",
            {"key": "value"},
            {"Authorization": "token"},
            10,
            verify="mock_cert.pem",
        )


def test_requests_http_client_post_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import typing

    import requests

    from src.domain_models.exceptions import AIServiceError

    def mock_post(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        msg = "Mock error"
        raise requests.HTTPError(msg)

    monkeypatch.setattr(requests, "post", mock_post)

    client = RequestsHTTPClient()


    monkeypatch.setattr(Path, "is_file", lambda self: True)

    with pytest.raises(AIServiceError, match="HTTP error"):
        client.post(
            "http://test.com",
            {"key": "value"},
            {"Authorization": "token"},
            10,
            verify="mock_cert.pem",
        )


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
