from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from src.container import ProductionDIContainer
from src.domain_models import (
    KnowledgeNode,
    PipelineConfig,
    PivotResponse,
    SemanticChunk,
    SummaryTree,
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
    def process(self, file_path: str) -> list[SemanticChunk]:
        msg = f"Cannot process file {file_path}: invalid format"
        raise ProcessingError(msg)

    def process_stream(self, file_path: str, chunk_size: int = 1000) -> Iterator[SemanticChunk]:
        yield SemanticChunk(id="1", text="test")


class MockKnowledgeGraphService(KnowledgeGraphService):
    def generate_raptor_tree(self, chunks: list[SemanticChunk]) -> SummaryTree:
        msg = "Failed to cluster chunks: not enough data"
        raise GraphError(msg)

    def generate_raptor_tree_batch(
        self, chunks: list[SemanticChunk], batch_size: int = 100
    ) -> SummaryTree:
        return self.generate_raptor_tree(chunks)

    def pivot_kj(self, tree: SummaryTree, axis: str) -> PivotResponse:
        msg = f"Invalid pivot axis '{axis}' provided"
        raise GraphError(msg)


class MockActiveLearningService(ActiveLearningService):
    def evaluate_answer(self, node: KnowledgeNode, answer: str) -> bool:
        msg = "Failed to evaluate answer safely"
        raise ActiveLearningError(msg)

    def generate_question(self, node: KnowledgeNode, difficulty: str = "normal") -> str:
        msg = "Could not generate contextually appropriate question"
        raise ActiveLearningError(msg)

    def track_progress(self, user_id: str, node_id: str, success: bool) -> None:
        pass

    def get_feedback(self, node: KnowledgeNode, answer: str) -> str:
        return ""


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


def test_container_initialization_success() -> None:
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
        container.document_processor.process(test_path)

    with pytest.raises(GraphError):
        container.knowledge_graph.generate_raptor_tree([])


def test_container_initialization_failures() -> None:
    config = PipelineConfig()

    with pytest.raises(ValueError, match="PipelineConfig must be provided."):
        ProductionDIContainer(
            None, get_llm_factory(), get_doc_factory(), get_kg_factory(), get_al_factory()
        )

    with pytest.raises(ValueError, match="LLMProtocol factory or instance must be provided."):
        ProductionDIContainer(config, None, get_doc_factory(), get_kg_factory(), get_al_factory())

    with pytest.raises(
        ValueError, match="DocumentProcessingService factory or instance must be provided."
    ):
        ProductionDIContainer(config, get_llm_factory(), None, get_kg_factory(), get_al_factory())

    with pytest.raises(
        ValueError, match="KnowledgeGraphService factory or instance must be provided."
    ):
        ProductionDIContainer(config, get_llm_factory(), get_doc_factory(), None, get_al_factory())

    with pytest.raises(
        ValueError, match="ActiveLearningService factory or instance must be provided."
    ):
        ProductionDIContainer(config, get_llm_factory(), get_doc_factory(), get_kg_factory(), None)
