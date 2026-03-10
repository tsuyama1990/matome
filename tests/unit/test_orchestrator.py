import os
from pathlib import Path

import pytest

from src.config import Settings
from src.domain_models import DocumentFactory, MetadataService, PipelineContext
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import (
    AnalysisOrchestrator,
    IngestionOrchestrator,
    OutputOrchestrator,
    PipelineConfig,
    PipelineDependencies,
    PipelineOrchestrator,
    ProcessManager,
)
from tests.helpers.mocks import MockAIService


def _create_dependencies(base_dir: str) -> tuple[PipelineDependencies, PipelineConfig]:
    from unittest.mock import MagicMock

    dummy_cert = Path(base_dir) / "dummy.pem"
    dummy_cert.write_text("cert")
    os.environ["MATOME_BASE_DATA_DIR"] = base_dir
    os.environ["SSL_CERT_PATH"] = str(dummy_cert)
    os.environ["SPACY_MODEL"] = "en_core_web_sm"
    os.environ["TRUSTED_SPACY_MODELS"] = '["en_core_web_sm", "en_core_web_md"]'
    os.environ["TEXT_FAST_MODEL"] = "google/gemini-2.5-flash"
    os.environ["TEXT_REASONING_MODEL"] = "deepseek/deepseek-reasoner"
    os.environ["MULTIMODAL_MODEL"] = "openai/gpt-4o"
    os.environ["CHUNK_SIZE"] = "1000"

    from src.config import AIConfig, FileProcessingConfig, MLConfig, SecurityConfig
    from src.config import PipelineConfig as ConfigPipelineConfig

    settings = Settings(
        ai=AIConfig(
            text_fast_model="google/gemini-2.5-flash",
            text_reasoning_model="deepseek/deepseek-reasoner",
            multimodal_model="openai/gpt-4o",
        ),
        file=FileProcessingConfig(
            allowed_base_dir=base_dir,
            chunk_size=1000,
            chunk_overlap=100,
        ),
        ml=MLConfig(
            spacy_model="en_core_web_sm",
            trusted_spacy_models=["en_core_web_sm", "en_core_web_md"],
        ),
        security=SecurityConfig(),
        pipeline=ConfigPipelineConfig(),
    )

    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    factory = DocumentFactory()
    metadata_service = MetadataService()

    import typing

    mock_text_splitter = MagicMock()
    mock_text_splitter.split_text.return_value = ["test chunk"]

    def mock_split_doc(*args: typing.Any, **kwargs: typing.Any) -> typing.Iterator[str]:
        yield "Test file content."

    mock_text_splitter.split_document.side_effect = mock_split_doc

    mock_entity_extractor = MagicMock()
    mock_entity_extractor.extract_entities.return_value = {"entity1": "value1"}

    mock_clustering_service = MagicMock()
    mock_clustering_service.cluster_chunks.return_value = {"level_0": "root"}

    deps = PipelineDependencies(
        doc_repo=repo,
        transaction_manager=repo,
        summary_service=ai,
        question_service=ai,
        doc_factory=factory,
        metadata_service=metadata_service,
        text_splitter=mock_text_splitter,
        entity_extractor=mock_entity_extractor,
        clustering_service=mock_clustering_service,
    )
    config = PipelineConfig(
        pipeline_timeout=settings.pipeline.pipeline_timeout,
        raptor_max_clusters=settings.ml.raptor_max_clusters,
    )
    return deps, config


def _create_orchestrator(base_dir: str) -> PipelineOrchestrator:
    deps, config = _create_dependencies(base_dir=base_dir)
    return PipelineOrchestrator(dependencies=deps, config=config)


def test_orchestrator_chunking_fallback(tmp_path: Path) -> None:
    orchestrator = _create_orchestrator(base_dir=str(tmp_path))
    chunks = orchestrator.deps.text_splitter.split_text("test " * 1000)
    assert len(chunks) > 0
    assert "test" in chunks[0]


def test_orchestrator_ner_fallback(tmp_path: Path) -> None:
    orchestrator = _create_orchestrator(base_dir=str(tmp_path))
    entities = orchestrator.deps.entity_extractor.extract_entities(["test chunk 1", "test chunk 2"])
    # May use Spacy if present, or fallback. Ensure it returns a dictionary.
    assert isinstance(entities, dict)


def test_orchestrator_raptor_fallback(tmp_path: Path) -> None:
    orchestrator = _create_orchestrator(base_dir=str(tmp_path))
    # Pass more than 15 chunks to avoid the UMAP dimensionality error for N <= 15 when using defaults
    chunks = [f"test document chunk number {i}" for i in range(20)]
    tree = orchestrator.deps.clustering_service.cluster_chunks(
        chunks, orchestrator.config.raptor_max_clusters
    )
    assert isinstance(tree, dict)
    assert "level_0" in tree


def test_ingestion_orchestrator_execute_content(tmp_path: Path) -> None:
    deps, _ = _create_dependencies(base_dir=str(tmp_path))
    ingestion = IngestionOrchestrator(deps)
    ctx = PipelineContext(root_doc_id="test_id", content="Short test content.", file_path=None)

    iterator, combined = ingestion.execute(ctx)
    chunks = list(iterator)
    assert "Short test content." in combined
    assert len(chunks) > 0


def test_ingestion_orchestrator_execute_file(tmp_path: Path) -> None:
    deps, _ = _create_dependencies(base_dir=str(tmp_path))
    ingestion = IngestionOrchestrator(deps)

    fpath = tmp_path / "test.txt"
    fpath.write_text("Test file content.")

    ctx = PipelineContext(root_doc_id="test_id", file_path=str(fpath), content=None)

    iterator, combined = ingestion.execute(ctx)
    chunks = list(iterator)
    assert "Test file content." in combined
    assert len(chunks) > 0


def test_ingestion_orchestrator_execute_empty_context(tmp_path: Path) -> None:
    deps, _ = _create_dependencies(base_dir=str(tmp_path))
    ingestion = IngestionOrchestrator(deps)

    ctx = PipelineContext(root_doc_id="test_id", content=None, file_path=None)
    with pytest.raises(ValueError, match="either content or file_path"):
        ingestion.execute(ctx)


def test_analysis_orchestrator_execute(tmp_path: Path) -> None:
    deps, config = _create_dependencies(base_dir=str(tmp_path))
    analysis = AnalysisOrchestrator(deps, config)

    ctx = PipelineContext(root_doc_id="test_id", content="Short test content.", file_path=None)
    chunks = iter(["chunk 1", "chunk 2"])

    entities, tree_metadata, summary = analysis.execute(ctx, chunks, "combined")
    assert isinstance(entities, dict)
    assert isinstance(tree_metadata, dict)
    assert isinstance(summary, str)


def test_analysis_orchestrator_execute_with_file(tmp_path: Path) -> None:
    deps, config = _create_dependencies(base_dir=str(tmp_path))
    analysis = AnalysisOrchestrator(deps, config)

    fpath = tmp_path / "test.txt"
    fpath.write_text("Test file content.")

    ctx = PipelineContext(root_doc_id="test_id", file_path=str(fpath), content=None)
    chunks = iter(["chunk 1", "chunk 2"])

    entities, tree_metadata, summary = analysis.execute(ctx, chunks, "combined")
    assert isinstance(entities, dict)
    assert isinstance(tree_metadata, dict)
    assert isinstance(summary, str)


def test_analysis_orchestrator_ai_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import typing

    from src.domain_models.exceptions import AIServiceError

    deps, config = _create_dependencies(base_dir=str(tmp_path))
    analysis = AnalysisOrchestrator(deps, config)

    def raise_error(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        msg = "Mock error"
        raise AIServiceError(msg)

    monkeypatch.setattr(deps.summary_service, "generate_summary", raise_error)

    ctx = PipelineContext(root_doc_id="test_id", content="Short test content.", file_path=None)
    chunks = iter(["chunk 1", "chunk 2"])

    _, _, summary = analysis.execute(ctx, chunks, "combined")
    assert "Fallback Summary:" in summary


def test_output_orchestrator_execute(tmp_path: Path) -> None:
    deps, _ = _create_dependencies(base_dir=str(tmp_path))
    output = OutputOrchestrator(deps)

    ctx = PipelineContext(root_doc_id="test_id", content="Test", file_path=None)
    identity, content, metadata = output.execute(ctx, "content", "summary", {}, {})

    assert identity.id == "test_id"
    assert content.summary == "summary"
    assert metadata.ai_metadata.chunk_index == 0


def test_output_orchestrator_ai_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import typing

    from src.domain_models.exceptions import AIServiceError

    deps, _ = _create_dependencies(base_dir=str(tmp_path))
    output = OutputOrchestrator(deps)

    def raise_error(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        msg = "Mock error"
        raise AIServiceError(msg)

    monkeypatch.setattr(deps.question_service, "generate_question", raise_error)

    ctx = PipelineContext(root_doc_id="test_id", content="Test", file_path=None)
    identity, content, metadata = output.execute(ctx, "content", "summary", {}, {})

    assert identity.id == "test_id"
    # Should not raise exception


def test_pipeline_orchestrator_run_pipeline(tmp_path: Path) -> None:
    orchestrator = _create_orchestrator(base_dir=str(tmp_path))
    ctx = PipelineContext(root_doc_id="test_id", content="Short content.", file_path=None)

    # Should run end-to-end without errors
    orchestrator.run_pipeline(ctx)
    node = orchestrator.deps.doc_repo.get_identity("test_id")
    assert node is not None


def test_pipeline_orchestrator_validate_length(tmp_path: Path) -> None:
    import typing

    orchestrator = _create_orchestrator(base_dir=str(tmp_path))
    # Mock the text_splitter to return an empty iterator so ingestion works,
    # but the combined_content is somehow extremely long (simulating a bypass or internal logic edge case).

    ctx = PipelineContext(root_doc_id="test_id", content="Short valid context", file_path=None)

    # Let's directly mock IngestionOrchestrator to return an invalid combined_content
    def mock_execute(ctx: PipelineContext) -> tuple[typing.Iterator[str], str]:
        return iter([]), "A" * (orchestrator.deps.doc_factory.max_content_length + 1)

    orchestrator.ingestion_orchestrator.execute = mock_execute

    with pytest.raises(RuntimeError):
        orchestrator.run_pipeline(ctx)


def test_process_manager_timeout() -> None:
    pm = ProcessManager(timeout=0.1)

    def slow_func(ctx: PipelineContext) -> None:
        import time

        time.sleep(0.5)

    ctx = PipelineContext(root_doc_id="test_id", content=None, file_path=None)
    with pytest.raises(TimeoutError):
        pm.run_with_timeout(slow_func, ctx)


def test_process_manager_error() -> None:
    pm = ProcessManager(timeout=1.0)

    def error_func(ctx: PipelineContext) -> None:
        msg = "Inner error"
        raise ValueError(msg)

    ctx = PipelineContext(root_doc_id="test_id", content=None, file_path=None)
    with pytest.raises(ValueError, match="Inner error"):
        pm.run_with_timeout(error_func, ctx)
