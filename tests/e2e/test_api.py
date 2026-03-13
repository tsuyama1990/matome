from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.domain_models import RaptorNode
from src.interfaces.api_router import router
from src.interfaces.dependencies import DIContainer, LLMProtocol
from src.interfaces.repository import DocumentRepositoryProtocol

app = FastAPI()
app.include_router(router)


class MockLLM(LLMProtocol):
    async def generate(self, prompt: str) -> str:
        if "generate a single, thought-provoking question" in prompt:
            return "What is the capital of France?"
        return "Good job. You are correct. Keep it up!"


class MockRepository(DocumentRepositoryProtocol):
    def get_node_by_id(self, node_id: str) -> RaptorNode:
        return RaptorNode(
            node_id=node_id,
            level=0,
            children_ids=[],
            summarized_content="This is a dense summary about system actors and state transitions.",
            is_unlocked=False,
        )

    def save_node(self, node: RaptorNode) -> None:
        pass


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    container = DIContainer()
    container.register(LLMProtocol, MockLLM)  # type: ignore[type-abstract]
    container.register(DocumentRepositoryProtocol, MockRepository)  # type: ignore[type-abstract]

    app.state.container = container

    with TestClient(app) as test_client:
        yield test_client


def test_get_question(client: TestClient) -> None:
    response = client.get("/nodes/test-node-123/question")
    assert response.status_code == 200
    assert response.json() == {"question": "What is the capital of France?"}


def test_unlock_node_valid(client: TestClient) -> None:
    response = client.post("/nodes/test-node-123/unlock", json={"user_answer": "Paris"})
    assert response.status_code == 200
    data = response.json()
    assert "Good job" in data["feedback"]
    assert data["is_unlocked"] is True
    assert "dense summary" in data["summarized_content"]


def test_unlock_node_invalid_crlf(client: TestClient) -> None:
    response = client.post("/nodes/test-node-123/unlock", json={"user_answer": "   \n "})
    assert response.status_code == 422
    data = response.json()
    assert "Answer cannot be empty" in data["detail"][0]["msg"]


def test_unlock_node_too_long(client: TestClient) -> None:
    response = client.post("/nodes/test-node-123/unlock", json={"user_answer": "A" * 5001})
    assert response.status_code == 422
    data = response.json()
    assert "String should have at most 5000 characters" in data["detail"][0]["msg"]


def test_unlock_node_missing_payload(client: TestClient) -> None:
    response = client.post("/nodes/test-node-123/unlock", json={})
    assert response.status_code == 422
