from pathlib import Path

import pytest

from src.domain_models import SemanticChunk, KnowledgeNode, SummaryTree, NodeState
from src.interfaces import LLMError, ProcessingError, GraphError, ActiveLearningError
from src.services.llm import DefaultLLMProtocol
from src.services.document import DefaultDocumentProcessingService
from src.services.graph import DefaultKnowledgeGraphService
from src.services.learning import DefaultActiveLearningService

def test_default_llm_protocol() -> None:
    llm = DefaultLLMProtocol()

    with pytest.raises(LLMError, match="Prompt cannot be empty"):
        llm.invoke("")

    res = llm.invoke("Test prompt")
    assert "Test prompt" in res


def test_default_document_processing_service(tmp_path: Path) -> None:
    doc_service = DefaultDocumentProcessingService()

    # Test valid
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello\nWorld\n")

    chunks = doc_service.process(str(test_file))
    assert len(chunks) == 1
    assert "Hello" in chunks[0].text

    # Test file not found (OSError)
    with pytest.raises(ProcessingError, match="Failed to securely read file"):
        doc_service.process(str(tmp_path / "missing.txt"))


def test_default_knowledge_graph_service() -> None:
    kg = DefaultKnowledgeGraphService()

    with pytest.raises(GraphError, match="Cannot generate graph from empty chunks"):
        kg.generate_raptor_tree([])

    chunks = [SemanticChunk(id="1", text="data")]
    tree = kg.generate_raptor_tree_batch(chunks)
    assert tree.root_node_id == "root"
    assert "root" in tree.nodes

    with pytest.raises(GraphError, match="Axis must be defined"):
        kg.pivot_kj(tree, "")

    res = kg.pivot_kj(tree, "Time")
    assert res.axis == "Time"


def test_default_active_learning_service() -> None:
    al = DefaultActiveLearningService()
    node = KnowledgeNode(id="1", title="T", summary="S", state=NodeState.LOCKED)

    with pytest.raises(ActiveLearningError, match="Answer cannot be empty"):
        al.evaluate_answer(node, "")

    assert al.evaluate_answer(node, "A good answer") is True
    assert al.evaluate_answer(node, "Bad") is False

    q = al.generate_question(node, "hard")
    assert "hard difficulty" in q

    unlocked_node = KnowledgeNode(id="2", title="T", summary="S", state=NodeState.UNLOCKED)
    with pytest.raises(ActiveLearningError, match="Cannot generate question for unlocked node"):
        al.generate_question(unlocked_node)

    assert al.get_feedback(node, "A") != ""
    al.track_progress("user1", "node1", True) # Should not raise
