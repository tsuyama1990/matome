import uuid
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.pivot_workflow import PivotEngine, ExportService
from src.domain_models import ChunkMetadata, EnrichedDocument, SemanticChunk
from src.interfaces.api_router import router
from src.interfaces.dependencies import DIContainer, LLMProtocol, VectorDBProtocol, EmbeddingProtocol
from src.interfaces.repository import DocumentRepositoryProtocol

app = FastAPI()
app.include_router(router)


class MockE2EPivotLLM(LLMProtocol):
    async def generate(self, prompt: str) -> str:
        if "sequence diagram" in prompt.lower() or "mermaid" in prompt.lower():
            return "```mermaid\nsequenceDiagram\n    A->>B: message\n```"
        if "markdown" in prompt.lower() or "requirements" in prompt.lower():
            return "## Requirements\n\n- System must approve budget."
        return "Generic response."


class MockE2EPivotRepository(DocumentRepositoryProtocol):
    def get_document_by_id(self, document_id: str) -> EnrichedDocument:
        chunk = SemanticChunk(
            id=uuid.uuid4(),
            content="Line managers approve budgets.",
            embedding=[0.1] * 768,
            metadata=ChunkMetadata(source_file="test.txt", actor_axis="Manager"),
        )
        return EnrichedDocument(
            document_id=uuid.UUID(document_id),
            original_text="Line managers approve budgets.",
            chunks=[chunk],
            raptor_nodes=[],
        )

    def save_document(self, document: EnrichedDocument) -> None:
        pass


@pytest.fixture
def pivot_client() -> Generator[TestClient, None, None]:
    container = DIContainer()
    container.register_singleton(LLMProtocol, MockE2EPivotLLM())  # type: ignore[type-abstract]
    container.register_singleton(DocumentRepositoryProtocol, MockE2EPivotRepository())  # type: ignore[type-abstract]

    # We must also register PivotEngine for the API
    def test_pivot_factory() -> PivotEngine:
        from unittest.mock import AsyncMock, MagicMock
        from src.domain_models.pivot import PivotState, PivotNode
        mock_db = MagicMock(spec=VectorDBProtocol)
        mock_embed = MagicMock(spec=EmbeddingProtocol)
        mock_engine = MagicMock(spec=PivotEngine)

        chunk_id = uuid.uuid4()
        mock_state = PivotState(
            original_document_id=uuid.uuid4(),
            axis_name="actor",
            nodes=[PivotNode(node_id="1", label="Actor", summary="Actor test", source_chunk_ids=[chunk_id])]
        )
        mock_engine.execute_pivot = AsyncMock(return_value=mock_state) # type: ignore[method-assign]

        # In actual pivot_workflow execute uses payload.axis which triggers the validation and logic
        # For the invalid axis test, we should mock the exception thrown if it's invalid_axis
        async def mock_execute(document, axis):
            if axis == "invalid_axis":
                from src.application.pivot_workflow import PivotGenerationError
                raise PivotGenerationError("Invalid axis")
            return mock_state

        mock_engine.execute_pivot.side_effect = mock_execute
        return mock_engine

    container.register_singleton(PivotEngine, test_pivot_factory())
    container.register_singleton(ExportService, ExportService())

    from src.interfaces.dependencies import register_pivot_workflow

    register_pivot_workflow(container)

    app.state.container = container

    with TestClient(app) as test_client:
        yield test_client


def test_pivot_valid_axis(pivot_client: TestClient) -> None:
    doc_id = str(uuid.uuid4())
    response = pivot_client.post(f"/documents/{doc_id}/pivot", json={"axis": "actor"})
    assert response.status_code == 200
    data = response.json()
    assert "mermaid" in data
    assert "markdown" in data
    assert "sequenceDiagram" in data["mermaid"]
    assert "Requirements" in data["markdown"]


def test_pivot_invalid_axis(pivot_client: TestClient) -> None:
    doc_id = str(uuid.uuid4())
    response = pivot_client.post(f"/documents/{doc_id}/pivot", json={"axis": "invalid_axis"})
    assert response.status_code == 400
    assert "Invalid axis" in response.json()["detail"]
