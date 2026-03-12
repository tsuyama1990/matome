from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.document import DocumentProcessor, RAPTORKnowledgeGraphService
from src.domain_models.chunk import ChunkMetadata, SemanticChunk
from src.domain_models.config import PipelineConfig
from src.domain_models.state import GraphState
from src.interfaces import LLMProtocol


def test_document_processor_path_traversal() -> None:
    processor = DocumentProcessor()

    with pytest.raises(ValueError, match="Path traversal attempt blocked."):
        list(processor.process_stream("../../etc/passwd"))

    with pytest.raises(ValueError, match="Path traversal attempt blocked."):
        list(processor.process_stream("/etc/passwd"))


def test_document_processor_file_not_found() -> None:
    processor = DocumentProcessor()

    with pytest.raises(ValueError, match="File not found: "):
        list(processor.process_stream("nonexistent_file.txt"))


def test_document_processor_max_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = PipelineConfig(max_chunk_scan_size=10)
    processor = DocumentProcessor(config=config)

    test_file = tmp_path / "large_file.txt"
    test_file.write_text("This file is way larger than ten bytes.")

    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    with pytest.raises(ValueError, match="File size exceeds maximum allowed size"):
        list(processor.process_stream(str(test_file)))


def test_document_processor_successful_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = PipelineConfig()
    processor = DocumentProcessor(config=config)

    test_file = tmp_path / "valid_file.txt"
    test_file.write_text("chunk 1 text. chunk 2 text.", encoding="utf-8")

    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    chunks = list(processor.process_stream(str(test_file), chunk_size=10))

    assert len(chunks) > 0
    assert chunks[0].text.startswith("chunk 1")
    assert chunks[0].metadata.source_document == str(test_file.resolve(strict=True))


def test_generate_raptor_tree_deterministic() -> None:
    # 1. Setup mock LLM Gateway
    mock_llm = MagicMock(spec=LLMProtocol)
    mock_llm.invoke.return_value = "Mocked Chain of Density Summary"

    # 2. Setup service
    config = PipelineConfig()
    service = RAPTORKnowledgeGraphService(llm_gateway=mock_llm, config=config)

    # 3. Create dummy chunks
    chunks = []
    for i in range(20):
        chunk = SemanticChunk(
            id=f"chunk_{i}",
            text=f"This is semantic chunk number {i} for testing RAPTOR.",
            metadata=ChunkMetadata(source_document="test", page_number=1),
        )
        chunks.append(chunk)

    state = GraphState(chunks=chunks)

    # 4. Generate Tree
    new_state = service.generate_raptor_tree(state)

    # 5. Verify the tree structure is deterministic
    assert new_state.tree is not None
    assert new_state.tree.root_node_id is not None
    assert new_state.tree.root_node_id in new_state.tree.nodes

    root_node = new_state.tree.nodes[new_state.tree.root_node_id]
    assert root_node.title == "Root Node"
    assert root_node.summary == "Mocked Chain of Density Summary"

    # GMM deterministic output validation (with 5 components and 20 chunks)
    cluster_nodes = [n for n in new_state.tree.nodes.values() if n.title.startswith("Cluster")]
    assert len(cluster_nodes) > 0
    assert len(cluster_nodes) <= 5

    # Check LLM was called at least for the clusters + root
    assert mock_llm.invoke.call_count == len(cluster_nodes) + 1


def test_generate_raptor_tree_batch_limits() -> None:
    mock_llm = MagicMock(spec=LLMProtocol)
    mock_llm.invoke.return_value = "Mocked Summary"

    config = PipelineConfig()
    service = RAPTORKnowledgeGraphService(llm_gateway=mock_llm, config=config)

    # Create 150 chunks
    chunks = []
    for i in range(150):
        chunk = SemanticChunk(
            id=f"chunk_{i}",
            text=f"Chunk {i} text",
            metadata=ChunkMetadata(source_document="test", page_number=1),
        )
        chunks.append(chunk)

    state = GraphState(chunks=chunks)

    # Process with batch limit of 100
    new_state = service.generate_raptor_tree_batch(state, batch_size=100)

    assert new_state.tree is not None
    # Verify that only the first 100 chunks were added to the tree's leaf nodes
    leaf_nodes = [n for n in new_state.tree.nodes.values() if n.title.startswith("Chunk")]
    assert len(leaf_nodes) == 100

    # Process with full limit
    new_state_full = service.generate_raptor_tree_batch(state, batch_size=200)
    assert new_state_full.tree is not None
    leaf_nodes_full = [n for n in new_state_full.tree.nodes.values() if n.title.startswith("Chunk")]
    assert len(leaf_nodes_full) == 150
