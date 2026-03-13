import pytest
import uuid
from typing import Any

from src.application.pivot_workflow import PivotWorkflow
from src.application import PivotKJEngine
from src.domain_models import SemanticChunk, ChunkMetadata, EnrichedDocument
from src.domain_models.pivot import PivotRequestPayload

class MockRepository:
    def __init__(self, doc: EnrichedDocument | None = None, raise_error: bool = False):
        self.doc = doc
        self.raise_error = raise_error

    def get_document_by_id(self, document_id: str) -> EnrichedDocument:
        if self.raise_error:
            raise Exception("DB connection failed")
        if not self.doc:
            raise ValueError("Not found")
        return self.doc

class MockLLM:
    def __init__(self, raise_error: bool = False):
        self.raise_error = raise_error

    async def generate(self, prompt: str) -> str:
        if self.raise_error:
            raise Exception("LLM connection failed")
        return "mocked result"

@pytest.mark.asyncio
async def test_pivot_workflow_no_chunks() -> None:
    doc_id = str(uuid.uuid4())
    doc = EnrichedDocument(
        document_id=uuid.UUID(doc_id),
        original_text="test",
        chunks=[],
        raptor_nodes=[]
    )
    repo = MockRepository(doc)
    engine = PivotKJEngine()
    llm = MockLLM()
    workflow = PivotWorkflow(repository=repo, pivot_engine=engine, llm=llm) # type: ignore[arg-type]

    with pytest.raises(ValueError, match="has no chunks"):
        await workflow.execute(doc_id, PivotRequestPayload(axis="actor"))

@pytest.mark.asyncio
async def test_pivot_workflow_repo_error() -> None:
    repo = MockRepository(raise_error=True)
    engine = PivotKJEngine()
    llm = MockLLM()
    workflow = PivotWorkflow(repository=repo, pivot_engine=engine, llm=llm) # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Failed to retrieve document"):
        await workflow.execute("doc-1", PivotRequestPayload(axis="actor"))

@pytest.mark.asyncio
async def test_pivot_workflow_llm_error() -> None:
    doc_id = str(uuid.uuid4())
    chunk = SemanticChunk(
        id=uuid.uuid4(),
        content="test",
        embedding=[0.0]*768,
        metadata=ChunkMetadata(source_file="test", actor_axis="Manager")
    )
    doc = EnrichedDocument(
        document_id=uuid.UUID(doc_id),
        original_text="test",
        chunks=[chunk],
        raptor_nodes=[]
    )
    repo = MockRepository(doc)
    engine = PivotKJEngine()
    llm = MockLLM(raise_error=True)
    workflow = PivotWorkflow(repository=repo, pivot_engine=engine, llm=llm) # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="Failed to generate markdown and mermaid artifacts"):
        await workflow.execute(doc_id, PivotRequestPayload(axis="actor"))
