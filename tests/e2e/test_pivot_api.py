import uuid
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.pivot_workflow import ExportService, PivotEngine
from src.domain_models import ChunkMetadata, EnrichedDocument, RaptorNode, SemanticChunk
from src.interfaces.api_router import router
from src.interfaces.dependencies import (
    DIContainer,
    LLMProtocol,
)
from src.interfaces.repository import DocumentRepositoryProtocol

app = FastAPI()
app.include_router(router)


class FallbackE2EPivotLLM(LLMProtocol):
    async def generate(self, prompt: str) -> str:
        if "sequence diagram" in prompt.lower() or "mermaid" in prompt.lower():
            return "```mermaid\nsequenceDiagram\n    A->>B: message\n```"
        if "markdown" in prompt.lower() or "requirements" in prompt.lower():
            return "## Requirements\n\n- System must approve budget."
        return "Generic response."

    async def generate_text(self, prompt: str, model: str) -> str:
        return await self.generate(prompt)


class FallbackE2EPivotRepository(DocumentRepositoryProtocol):
    def get_document_by_id(self, document_id: str | uuid.UUID) -> EnrichedDocument:
        chunk = SemanticChunk(
            id=uuid.uuid4(),
            content="Line managers approve budgets.",
            embedding=[0.1] * 768,
            metadata=ChunkMetadata(source_file="test.txt", actor_axis="Manager"),
        )
        return EnrichedDocument(
            document_id=uuid.UUID(str(document_id)),
            original_text="Line managers approve budgets.",
            chunks=[chunk],
            raptor_nodes=[],
        )

    def save_document(self, document: EnrichedDocument) -> None:
        pass

    def get_node_by_id(self, node_id: str) -> "RaptorNode":
        from src.domain_models import RaptorNode

        return RaptorNode(node_id=node_id, level=0, summarized_content="fallback")

    def save_node(self, node: "RaptorNode") -> None:
        pass

    def save_nodes_batch(self, nodes: list["RaptorNode"]) -> None:
        pass

    import contextlib

    @contextlib.contextmanager
    def transaction(self) -> Generator[None, None, None]:
        yield


@pytest.fixture
def pivot_client() -> Generator[TestClient, None, None]:
    container = DIContainer()

    def llm_factory() -> LLMProtocol:
        return FallbackE2EPivotLLM()

    def repo_factory() -> DocumentRepositoryProtocol:
        return FallbackE2EPivotRepository()

    container.register(LLMProtocol, llm_factory)  # type: ignore[type-abstract]
    container.register(DocumentRepositoryProtocol, repo_factory)  # type: ignore[type-abstract]

    # We must also register PivotEngine for the API
    def test_pivot_factory() -> PivotEngine:
        from unittest.mock import AsyncMock, MagicMock

        from src.domain_models.pivot import PivotNode, PivotState

        fallback_engine = MagicMock(spec=PivotEngine)

        chunk_id = uuid.uuid4()
        fallback_state = PivotState(
            original_document_id=uuid.uuid4(),
            axis_name="actor",
            nodes=[
                PivotNode(
                    node_id="1", label="Actor", summary="Actor test", source_chunk_ids=[chunk_id]
                )
            ],
        )
        fallback_engine.execute_pivot = AsyncMock(return_value=fallback_state)

        # In actual pivot_workflow execute uses payload.axis which triggers the validation and logic
        # For the invalid axis test, we should fallback the exception thrown if it's invalid_axis
        async def fallback_execute(document: EnrichedDocument, axis: str) -> PivotState:
            if axis == "invalid_axis":
                from src.application.pivot_workflow import PivotGenerationError

                msg = "Invalid axis"
                raise PivotGenerationError(msg)
            return fallback_state

        fallback_engine.execute_pivot.side_effect = fallback_execute
        return fallback_engine

    container.register(PivotEngine, test_pivot_factory)

    def test_export_factory() -> ExportService:
        return ExportService()

    container.register(ExportService, test_export_factory)

    from src.interfaces.dependencies import register_pivot_workflow

    register_pivot_workflow(container)

    app.state.container = container

    with TestClient(app) as test_client:
        yield test_client


def test_pivot_valid_axis(pivot_client: TestClient) -> None:
    doc_id = str(uuid.uuid4())
    response = pivot_client.post(f"/documents/{doc_id}/pivot", json={"axis": "actor"})
    assert response.status_code == 200, f"Response detail: {response.json()}"
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
