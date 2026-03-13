import uuid

import pytest

from src.application import PivotKJEngine
from src.application.pivot_workflow import PivotWorkflow
from src.domain_models import ChunkMetadata, EnrichedDocument, SemanticChunk
from src.domain_models.pivot import PivotRequestPayload
from src.infrastructure.test_services import SafeTestDocumentRepository, SafeTestLLMService


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
