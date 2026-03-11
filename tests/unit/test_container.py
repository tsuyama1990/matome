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
    def invoke(self, prompt: str, **kwargs: Any) -> str:
        msg = "LLM invocation timeout simulated"
        raise LLMError(msg)


class MockDocumentProcessingService(DocumentProcessingService):
    def process(self, file_path: str) -> list[SemanticChunk]:
        msg = f"Cannot process file {file_path}: invalid format"
        raise ProcessingError(msg)


class MockKnowledgeGraphService(KnowledgeGraphService):
    def generate_raptor_tree(self, chunks: list[SemanticChunk]) -> SummaryTree:
        msg = "Failed to cluster chunks: not enough data"
        raise GraphError(msg)

    def pivot_kj(self, tree: SummaryTree, axis: str) -> PivotResponse:
        msg = f"Invalid pivot axis '{axis}' provided"
        raise GraphError(msg)


class MockActiveLearningService(ActiveLearningService):
    def evaluate_answer(self, node: KnowledgeNode, answer: str) -> bool:
        msg = "Failed to evaluate answer safely"
        raise ActiveLearningError(msg)

    def generate_question(self, node: KnowledgeNode) -> str:
        msg = "Could not generate contextually appropriate question"
        raise ActiveLearningError(msg)


def test_container_initialization_success() -> None:
    config = PipelineConfig()
    llm = MockLLMProtocol()
    doc = MockDocumentProcessingService()
    kg = MockKnowledgeGraphService()
    al = MockActiveLearningService()

    container = ProductionDIContainer(config, llm, doc, kg, al)
    assert container.config is config
    assert container.llm_gateway is llm
    assert container.document_processor is doc
    assert container.knowledge_graph is kg
    assert container.active_learning is al

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
    llm = MockLLMProtocol()
    doc = MockDocumentProcessingService()
    kg = MockKnowledgeGraphService()
    al = MockActiveLearningService()

    with pytest.raises(ValueError, match="PipelineConfig must be provided."):
        ProductionDIContainer(None, llm, doc, kg, al)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="LLMProtocol implementation must be provided."):
        ProductionDIContainer(config, None, doc, kg, al)  # type: ignore[arg-type]

    with pytest.raises(
        ValueError, match="DocumentProcessingService implementation must be provided."
    ):
        ProductionDIContainer(config, llm, None, kg, al)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="KnowledgeGraphService implementation must be provided."):
        ProductionDIContainer(config, llm, doc, None, al)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="ActiveLearningService implementation must be provided."):
        ProductionDIContainer(config, llm, doc, kg, None)  # type: ignore[arg-type]
