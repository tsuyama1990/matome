import uuid
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application import PivotKJEngine
from src.domain_models import ChunkMetadata, EnrichedDocument, SemanticChunk
from src.interfaces.api_router import router
from src.interfaces.dependencies import DIContainer, LLMProtocol
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
    container.register(LLMProtocol, MockE2EPivotLLM)  # type: ignore[type-abstract]
    container.register(DocumentRepositoryProtocol, MockE2EPivotRepository)  # type: ignore[type-abstract]

    # We must also register PivotKJEngine for the API
    container.register(PivotKJEngine, PivotKJEngine)

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
