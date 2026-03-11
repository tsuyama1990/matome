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
    ActiveLearningService,
    DocumentProcessingService,
    KnowledgeGraphService,
    LLMProtocol,
)


class MockLLMProtocol(LLMProtocol):
    def invoke(self, prompt: str, **kwargs: Any) -> str:
        return ""


class MockDocumentProcessingService(DocumentProcessingService):
    def process(self, file_path: str) -> list[SemanticChunk]:
        return []


class MockKnowledgeGraphService(KnowledgeGraphService):
    def generate_raptor_tree(self, chunks: list[SemanticChunk]) -> SummaryTree:
        return SummaryTree(root_node_id="r1")

    def pivot_kj(self, tree: SummaryTree, axis: str) -> PivotResponse:
        return PivotResponse(axis="a", restructured_nodes=[], mermaid_diagram="")


class MockActiveLearningService(ActiveLearningService):
    def evaluate_answer(self, node: KnowledgeNode, answer: str) -> bool:
        return False

    def generate_question(self, node: KnowledgeNode) -> str:
        return ""


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
