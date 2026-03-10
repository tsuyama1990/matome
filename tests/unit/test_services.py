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


def test_default_model_verifier_exceptions(tmp_path: Path) -> None:
    from src.infrastructure.services import DefaultModelVerifier

    verifier = DefaultModelVerifier({"trusted_model"}, {}, 1000)

    with pytest.raises(ValueError, match="Untrusted ML Model requested"):
        verifier.verify_model_signature("untrusted_model")

    with pytest.raises(ValueError, match="could not be imported"):
        verifier.verify_model_signature("trusted_model")


def test_default_model_verifier_signature_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:

    from src.infrastructure.services import DefaultModelVerifier

    # Create a dummy module inside a package
    pkg_dir = tmp_path / "dummy_module_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    dummy_module_path = pkg_dir / "dummy_module.py"

    # Must be valid python or it fails on import before reaching the signature check
    dummy_module_path.write_text("x = 'a' * 2000\n")

    monkeypatch.syspath_prepend(str(tmp_path))

    verifier = DefaultModelVerifier({"dummy_module_pkg.dummy_module"}, {"dummy_module_pkg.dummy_module": "hash"}, 10)
    with pytest.raises(ValueError, match="exceeds signature scanning limits"):
        verifier.verify_model_signature("dummy_module_pkg.dummy_module")


def test_default_model_verifier_hash_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.infrastructure.services import DefaultModelVerifier

    pkg_dir = tmp_path / "dummy_module_pkg2"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    dummy_module_path = pkg_dir / "dummy_module2.py"
    dummy_module_path.write_text("x = 1")
    monkeypatch.syspath_prepend(str(tmp_path))

    verifier = DefaultModelVerifier({"dummy_module_pkg2.dummy_module2"}, {"dummy_module_pkg2.dummy_module2": "invalidhash"}, 10000)
    with pytest.raises(ValueError, match="Cryptographic signature mismatch"):
        verifier.verify_model_signature("dummy_module_pkg2.dummy_module2")


class MockModelVerifier:
    def verify_model_signature(self, model_name: str) -> None:
        pass


class MockRateLimiter:
    def acquire(self) -> None:
        pass


def test_default_entity_extractor_invalid_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    import spacy.util

    from src.infrastructure.services import DefaultEntityExtractor, EntityExtractorConfig

    def mock_is_package(name: str) -> bool:
        return False

    monkeypatch.setattr(spacy.util, "is_package", mock_is_package)

    # We provide an invalid unclosed regex. It should fall back to the safe default
    # r"\b[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,3}\b" and extract "Apple Inc"
    config = EntityExtractorConfig("dummy", "[unclosed_regex")
    extractor = DefaultEntityExtractor(config, MockRateLimiter(), MockModelVerifier())

    entities = extractor.extract_entities(["Apple Inc."])
    assert "chunk_0_Fallback_ORG" in entities
    assert entities["chunk_0_Fallback_ORG"] == "Apple Inc"


def test_default_entity_extractor_nlp_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import spacy.util

    from src.infrastructure.services import DefaultEntityExtractor, EntityExtractorConfig

    def mock_is_package(name: str) -> bool:
        return False

    monkeypatch.setattr(spacy.util, "is_package", mock_is_package)

    config = EntityExtractorConfig("dummy_spacy_model", r"\b[A-Z][a-z]+\b")
    extractor = DefaultEntityExtractor(config, MockRateLimiter(), MockModelVerifier())

    # Will fallback to regex and log warning
    entities = extractor.extract_entities(["Apple Inc."])
    assert "chunk_0_Fallback_ORG" in entities
    assert entities["chunk_0_Fallback_ORG"] == "Apple"


def test_default_entity_extractor_container_isolation_sandbox() -> None:
    from src.infrastructure.services import DefaultEntityExtractor, EntityExtractorConfig

    config = EntityExtractorConfig("invalid_nonexistent_module", r"\b[A-Z][a-z]+\b")
    extractor = DefaultEntityExtractor(config, MockRateLimiter(), MockModelVerifier())

    # Isolation sandbox raises import error handled internally
    entities = extractor.extract_entities(["Microsoft"])
    assert "chunk_0_Fallback_ORG" in entities


def test_default_clustering_service_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import typing

    from src.infrastructure.services import DefaultClusteringService

    # Mock ML provider to raise import error simulating missing sklearn
    # In reality, without sklearn, we must fallback to a single root node graceful degradation.
    class BadMLProvider:
        def get_vectorizer(self) -> typing.Any:
            msg = "sklearn not found"
            raise ImportError(msg)
        def get_clusterer(self, a: int, b: int) -> typing.Any:
            pass

    service = DefaultClusteringService(42, BadMLProvider())

    chunks = ["chunk1", "chunk2", "chunk3"]
    result = service.cluster_chunks(chunks, 2)

    # Verify fallback mechanism returns a flat tree without crashing the ingestion orchestrator
    assert result["algorithm"] == "None (Missing ML modules)"
    assert result["level_0"] == "root"
    assert "clusters_found" not in result # Since it failed before actually clustering


def test_default_clustering_service_incremental_batching(monkeypatch: pytest.MonkeyPatch) -> None:
    import typing

    from src.infrastructure.services import DefaultClusteringService

    class MockMLClusteringProvider:
        def get_vectorizer(self) -> typing.Any:
            class MockVectorizer:
                def transform(self, data: typing.Any) -> typing.Any:
                    return data
            return MockVectorizer()

        def get_clusterer(self, max_clusters: int, random_seed: int) -> typing.Any:
            class MockClusterer:
                def __init__(self, max_clusters: int) -> None:
                    self.n_clusters = max_clusters
                def partial_fit(self, data: typing.Any) -> typing.Any:
                    pass
            return MockClusterer(max_clusters)

    service = DefaultClusteringService(42, MockMLClusteringProvider())

    # More than 100 chunks to trigger batching
    chunks = [f"chunk {i}" for i in range(150)]
    result = service.cluster_chunks(chunks, 2)
    assert result["total_chunks"] == "150"

def test_default_clustering_service_batch_less_than_max(monkeypatch: pytest.MonkeyPatch) -> None:
    import typing

    from src.infrastructure.services import DefaultClusteringService

    class MockMLClusteringProvider:
        def get_vectorizer(self) -> typing.Any:
            class MockVectorizer:
                def transform(self, data: typing.Any) -> typing.Any:
                    return data
            return MockVectorizer()

        def get_clusterer(self, max_clusters: int, random_seed: int) -> typing.Any:
            class MockClusterer:
                def __init__(self, max_clusters: int) -> None:
                    self.n_clusters = max_clusters
                def partial_fit(self, data: typing.Any) -> typing.Any:
                    pass
            return MockClusterer(max_clusters)

    service = DefaultClusteringService(42, MockMLClusteringProvider())

    # chunks < 100 but chunks > max_clusters
    chunks = [f"chunk {i}" for i in range(10)]
    result = service.cluster_chunks(chunks, 5)
    assert result["total_chunks"] == "10"


def test_default_clustering_service_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    import typing

    from src.infrastructure.services import DefaultClusteringService

    class BadMLProvider:
        def get_vectorizer(self) -> typing.Any:
            return self
        def transform(self, data: typing.Any) -> typing.Any:
            msg = "Unexpected Math Error"
            raise RuntimeError(msg)
        def get_clusterer(self, a: int, b: int) -> typing.Any:
            return self
        def partial_fit(self, data: typing.Any) -> typing.Any:
            msg = "Unexpected Math Error"
            raise RuntimeError(msg)

    service = DefaultClusteringService(42, BadMLProvider())
    result = service.cluster_chunks(["chunk1", "chunk2", "chunk3"], 2)
    assert "error_fallback" in result
    assert "Unexpected Math Error" in result["error_fallback"]


def test_requests_http_client_exceptions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import typing

    import requests

    from src.domain_models.exceptions import AIServiceError
    from src.infrastructure.services import RequestsHTTPClient

    cert_path = tmp_path / "cert.pem"
    cert_path.write_text("cert")

    client = RequestsHTTPClient(str(cert_path))

    # Test Timeout
    def mock_post_timeout(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        msg = "timed out"
        raise requests.Timeout(msg)

    monkeypatch.setattr(requests, "post", mock_post_timeout)
    with pytest.raises(AIServiceError, match="timed out"):
        client.post("http://mock", {}, {}, 10)

    # Test HTTPError
    def mock_post_http_error(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        msg = "http error"
        raise requests.HTTPError(msg)

    monkeypatch.setattr(requests, "post", mock_post_http_error)
    with pytest.raises(AIServiceError, match="http error"):
        client.post("http://mock", {}, {}, 10)

    # Test RequestException
    def mock_post_request_error(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        msg = "connection error"
        raise requests.RequestException(msg)

    monkeypatch.setattr(requests, "post", mock_post_request_error)
    with pytest.raises(AIServiceError, match="connection error"):
        client.post("http://mock", {}, {}, 10)

    # Test invalid cert path resolution
    client_invalid = RequestsHTTPClient()
    with pytest.raises(ValueError, match="CA bundle path was provided"):
        client_invalid.post("http://mock", {}, {}, 10)

    with pytest.raises(ValueError, match="CA bundle path is invalid"):
        client_invalid.post("http://mock", {}, {}, 10, verify="/does/not/exist.pem")


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

    import os
    from pathlib import Path

    monkeypatch.setattr(Path, "is_file", lambda self: True)
    monkeypatch.setattr(os.path, "realpath", lambda x: x)

    result = client.post(
        "http://test.com",
        {"key": "value"},
        {"Authorization": "token"},
        10,
        verify="mock_cert.pem",
    )
    assert result == {"test": "data"}


def test_requests_http_client_post_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import typing

    import requests

    from src.domain_models.exceptions import AIServiceError

    def mock_post(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        msg = "Mock error"
        raise requests.HTTPError(msg)

    monkeypatch.setattr(requests, "post", mock_post)

    client = RequestsHTTPClient()

    import os
    from pathlib import Path
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    monkeypatch.setattr(os.path, "realpath", lambda x: x)

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
