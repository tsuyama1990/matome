import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from cryptography.fernet import Fernet

from src.container import ProductionDIContainer
from src.domain_models import (
    GraphState,
    KnowledgeNode,
    PipelineConfig,
    SemanticChunk,
)
from src.interfaces import (
    ActiveLearningError,
    ActiveLearningService,
    DocumentProcessingService,
    GraphError,
    KnowledgeGraphService,
    LLMError,
    LLMProtocol,
    ProcessingError,
)


class MockLLMProtocol(LLMProtocol):
    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        msg = "LLM invocation timeout simulated"
        raise LLMError(msg)


class MockDocumentProcessingService(DocumentProcessingService):
    def process(self, state: GraphState) -> GraphState:
        msg = f"Cannot process file {state.file_path}: invalid format"
        raise ProcessingError(msg)

    def process_stream(self, file_path: str, chunk_size: int = 1000) -> Iterator[SemanticChunk]:
        yield SemanticChunk(id="1", text="test")


class MockKnowledgeGraphService(KnowledgeGraphService):
    def generate_raptor_tree(self, state: GraphState) -> GraphState:
        msg = "Failed to cluster chunks: not enough data"
        raise GraphError(msg)

    def generate_raptor_tree_batch(self, state: GraphState, batch_size: int = 100) -> GraphState:
        return self.generate_raptor_tree(state)

    def pivot_kj(self, state: GraphState) -> GraphState:
        msg = f"Invalid pivot axis '{state.pivot_axis}' provided"
        raise GraphError(msg)


class MockActiveLearningService(ActiveLearningService):
    def evaluate_answer(self, node: KnowledgeNode, answer: str) -> bool:
        msg = "Failed to evaluate answer safely"
        raise ActiveLearningError(msg)

    def generate_question(self, node: KnowledgeNode, difficulty: str = "normal") -> str:
        msg = "Could not generate contextually appropriate question"
        raise ActiveLearningError(msg)

    def track_progress(self, user_id: str, node_id: str, success: bool) -> None:
        msg = "Failed to securely track active learning progress"
        raise ActiveLearningError(msg)

    def get_feedback(self, node: KnowledgeNode, answer: str) -> str:
        msg = "Failed to generate targeted feedback securely"
        raise ActiveLearningError(msg)


def get_llm_factory() -> Callable[[], LLMProtocol]:
    def factory() -> LLMProtocol:
        return MockLLMProtocol()

    return factory


def get_doc_factory() -> Callable[[], DocumentProcessingService]:
    def factory() -> DocumentProcessingService:
        return MockDocumentProcessingService()

    return factory


def get_kg_factory() -> Callable[[], KnowledgeGraphService]:
    def factory() -> KnowledgeGraphService:
        return MockKnowledgeGraphService()

    return factory


def get_al_factory() -> Callable[[], ActiveLearningService]:
    def factory() -> ActiveLearningService:
        return MockActiveLearningService()

    return factory


@pytest.fixture
def mock_env_key() -> Any:
    return mock.patch.dict(
        os.environ, {"MATOME_ENCRYPTION_KEY": Fernet.generate_key().decode("utf-8")}
    )


def test_container_initialization_success(mock_env_key: Any) -> None:
    with mock_env_key:
        config = PipelineConfig()

        container = ProductionDIContainer(
            config=config,
            llm_gateway_factory=get_llm_factory(),
            document_processor_factory=get_doc_factory(),
            knowledge_graph_factory=get_kg_factory(),
            active_learning_factory=get_al_factory(),
        )

        assert container.config is config
        assert isinstance(container.llm_gateway, MockLLMProtocol)
        assert isinstance(container.document_processor, MockDocumentProcessingService)
        assert isinstance(container.knowledge_graph, MockKnowledgeGraphService)
        assert isinstance(container.active_learning, MockActiveLearningService)

        # Optionally ensure the mock methods throw as expected now to verify they act accordingly
        with pytest.raises(LLMError):
            container.llm_gateway.invoke("hello")

        test_path = str(Path.cwd() / "test.txt")
        with pytest.raises(ProcessingError):
            container.document_processor.process(GraphState(file_path=test_path))

        with pytest.raises(GraphError):
            container.knowledge_graph.generate_raptor_tree(GraphState(file_path="foo"))


def test_container_initialization_failures(mock_env_key: Any) -> None:
    with mock_env_key:
        config = PipelineConfig()

        # Test mypy overridden missing initialization values
        with pytest.raises(ValueError, match="PipelineConfig must be explicitly provided."):
            ProductionDIContainer(
                None,  # type: ignore[arg-type]
                get_llm_factory(),
                get_doc_factory(),
                get_kg_factory(),
                get_al_factory(),
            )

        with pytest.raises(
            ValueError, match="LLMProtocol factory function must be explicitly provided."
        ):
            ProductionDIContainer(
                config,
                None,  # type: ignore[arg-type]
                get_doc_factory(),
                get_kg_factory(),
                get_al_factory(),
            )

        with pytest.raises(
            ValueError,
            match="DocumentProcessingService factory function must be explicitly provided.",
        ):
            ProductionDIContainer(
                config,
                get_llm_factory(),
                None,  # type: ignore[arg-type]
                get_kg_factory(),
                get_al_factory(),
            )

        with pytest.raises(
            ValueError,
            match="KnowledgeGraphService factory function must be explicitly provided.",
        ):
            ProductionDIContainer(
                config,
                get_llm_factory(),
                get_doc_factory(),
                None,  # type: ignore[arg-type]
                get_al_factory(),
            )

        with pytest.raises(
            ValueError,
            match="ActiveLearningService factory function must be explicitly provided.",
        ):
            ProductionDIContainer(
                config,
                get_llm_factory(),
                get_doc_factory(),
                get_kg_factory(),
                None,  # type: ignore[arg-type]
            )

        # Type errors for non-callables
        with pytest.raises(TypeError, match="llm_gateway_factory must be a callable factory function."):
            ProductionDIContainer(
                config,
                MockLLMProtocol(),  # type: ignore[arg-type]
                get_doc_factory(),
                get_kg_factory(),
                get_al_factory(),
            )
