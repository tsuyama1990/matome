import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application import PivotKJEngine
from src.application.pivot_workflow import ExportService, PivotEngine, PivotWorkflow
from src.domain_models import ChunkMetadata, EnrichedDocument, SemanticChunk
from src.domain_models.pivot import PivotNode, PivotRequestPayload, PivotState
from src.infrastructure.test_services import SafeTestDocumentRepository, SafeTestLLMService
from src.interfaces.dependencies import EmbeddingProtocol, LLMProtocol, VectorDBProtocol


@pytest.mark.asyncio
async def test_pivot_workflow_no_chunks() -> None:
    doc_id = str(uuid.uuid4())
    doc = EnrichedDocument(
        document_id=uuid.UUID(doc_id), original_text="test", chunks=[], raptor_nodes=[]
    )
    repo = SafeTestDocumentRepository(doc)
    engine = PivotKJEngine(allowed_axes=frozenset({"actor"}))
    llm = SafeTestLLMService()
    workflow = PivotWorkflow(repository=repo, pivot_engine=engine, llm=llm)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="has no chunks"):
        await workflow.execute(doc_id, PivotRequestPayload(axis="actor"))


@pytest.mark.asyncio
async def test_pivot_workflow_repo_error() -> None:
    repo = SafeTestDocumentRepository(raise_error=True)
    engine = PivotKJEngine(allowed_axes=frozenset({"actor"}))
    llm = SafeTestLLMService()
    workflow = PivotWorkflow(repository=repo, pivot_engine=engine, llm=llm)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Failed to retrieve document"):
        await workflow.execute("doc-1", PivotRequestPayload(axis="actor"))


@pytest.mark.asyncio
async def test_pivot_workflow_llm_error() -> None:
    # Partial failure logic should not crash but return placeholder text.
    doc_id = str(uuid.uuid4())
    chunk = SemanticChunk(
        id=uuid.uuid4(),
        content="test",
        embedding=[0.0] * 768,
        metadata=ChunkMetadata(source_file="test", actor_axis="Manager"),
    )
    doc = EnrichedDocument(
        document_id=uuid.UUID(doc_id), original_text="test", chunks=[chunk], raptor_nodes=[]
    )
    repo = SafeTestDocumentRepository(doc)
    engine = PivotKJEngine(allowed_axes=frozenset({"actor"}))
    llm = SafeTestLLMService(raise_error=True)
    workflow = PivotWorkflow(repository=repo, pivot_engine=engine, llm=llm)  # type: ignore[arg-type]

    result = await workflow.execute(doc_id, PivotRequestPayload(axis="actor"))
    assert result["markdown"] == "Markdown generation failed."
    assert result["mermaid"] == "Mermaid generation failed."


@pytest.fixture
def mock_llm() -> LLMProtocol:
    return MagicMock(spec=LLMProtocol)

@pytest.fixture
def mock_vector_db() -> VectorDBProtocol:
    return MagicMock(spec=VectorDBProtocol)

@pytest.fixture
def mock_embedding() -> EmbeddingProtocol:
    return MagicMock(spec=EmbeddingProtocol)

@pytest.mark.asyncio
async def test_pivot_engine_orchestration(mock_llm: LLMProtocol, mock_vector_db: VectorDBProtocol, mock_embedding: EmbeddingProtocol) -> None:
    engine = PivotEngine(llm=mock_llm, vector_db=mock_vector_db, embedding=mock_embedding)
    doc_id = uuid.uuid4()
    doc = EnrichedDocument(document_id=doc_id, original_text="...", chunks=[], raptor_nodes=[])

    mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 384) # type: ignore[method-assign]

    chunk_id = uuid.uuid4()
    mock_chunk = SemanticChunk(
        id=chunk_id,
        content="Test content",
        embedding=[0.1] * 384,
        metadata=ChunkMetadata(source_file="test.txt", time_axis="Past")
    )
    mock_vector_db.search = AsyncMock(return_value=[mock_chunk]) # type: ignore[method-assign]

    mock_llm.generate = AsyncMock(return_value=f'{{"nodes": [{{"label": "Past Actor", "summary": "Did things.", "source_chunk_ids": ["{chunk_id!s}"]}}]}}') # type: ignore[method-assign]

    state = await engine.execute_pivot(doc, "Timeline")

    assert isinstance(state, PivotState)
    assert state.axis_name == "Timeline"
    assert len(state.nodes) == 1
    assert state.nodes[0].source_chunk_ids == [chunk_id]
    mock_vector_db.search.assert_called_once()
    mock_llm.generate.assert_called_once()

def test_export_service_markdown() -> None:
    service = ExportService()
    state = PivotState(
        original_document_id=uuid.uuid4(),
        axis_name="Data Flow",
        nodes=[
            PivotNode(node_id="1", label="Ingest", summary="Data goes in.", source_chunk_ids=[uuid.uuid4()]),
            PivotNode(node_id="2", label="Process", summary="Data is processed.", source_chunk_ids=[uuid.uuid4()])
        ]
    )

    markdown = service.generate_markdown(state)
    assert "# Data Flow" in markdown
    assert "## Ingest" in markdown
    assert "Data goes in." in markdown
    assert "## Process" in markdown
    assert "Data is processed." in markdown
