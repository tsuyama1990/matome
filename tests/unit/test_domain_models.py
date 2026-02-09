import pytest
from pydantic import ValidationError

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, Document, DocumentTree, SummaryNode


def test_document_validation() -> None:
    """Test valid and invalid Document creation."""
    # Valid
    doc = Document(content="hello", metadata={"source": "test"})
    assert doc.content == "hello"
    assert doc.metadata == {"source": "test"}

    # Invalid case: missing content
    with pytest.raises(ValidationError):
        Document(metadata={})  # type: ignore


def test_chunk_validation() -> None:
    """Test valid and invalid Chunk creation."""
    # Valid
    chunk = Chunk(
        index=0,
        text="chunk text",
        start_char_idx=0,
        end_char_idx=10,
        metadata={}
    )
    assert chunk.index == 0
    assert chunk.text == "chunk text"

    # Invalid case: negative index
    with pytest.raises(ValidationError):
        Chunk(index=-1, text="text", start_char_idx=0, end_char_idx=10)

    # Invalid case: start > end
    with pytest.raises(ValidationError):
        Chunk(index=0, text="text", start_char_idx=10, end_char_idx=5)


def test_summary_node_validation() -> None:
    """Test valid and invalid SummaryNode creation."""
    # Valid
    node = SummaryNode(
        id="node1",
        text="Summary of text",
        level=1,
        children_indices=[0, 1],
        metadata={}
    )
    assert node.level == 1
    assert node.children_indices == [0, 1]

    # Invalid case: level < 1
    with pytest.raises(ValidationError):
        SummaryNode(
            id="node1",
            text="Summary",
            level=0,  # Should be >= 1
            children_indices=[0]
        )


def test_cluster_validation() -> None:
    """Test valid and invalid Cluster creation."""
    # Valid
    cluster = Cluster(
        id="c1",
        level=0,
        node_indices=[0, 1, 2],
        centroid=[0.1, 0.2]
    )
    assert cluster.level == 0
    assert cluster.node_indices == [0, 1, 2]

    # Invalid case: level < 0
    with pytest.raises(ValidationError):
        Cluster(
            id="c1",
            level=-1,
            node_indices=[0]
        )


def test_document_tree_validation() -> None:
    """Test DocumentTree structure validation."""
    # Setup components
    chunk1 = Chunk(index=0, text="A", start_char_idx=0, end_char_idx=1)
    chunk2 = Chunk(index=1, text="B", start_char_idx=1, end_char_idx=2)
    summary = SummaryNode(
        id="s1",
        text="AB",
        level=1,
        children_indices=[0, 1]
    )

    # Valid DocumentTree
    tree = DocumentTree(
        root_node=summary,
        all_nodes={"s1": summary},
        leaf_chunks=[chunk1, chunk2],
        metadata={}
    )
    assert tree.root_node.id == "s1"
    assert len(tree.leaf_chunks) == 2
    assert len(tree.all_nodes) == 1
    assert tree.all_nodes["s1"] == summary


def test_config_validation() -> None:
    """Test ProcessingConfig validation."""
    # Valid
    config = ProcessingConfig(max_tokens=100, overlap=10)
    assert config.max_tokens == 100

    # Test new fields
    config_default = ProcessingConfig.default()
    assert config_default.clustering_algorithm.value == "gmm"
    assert config_default.summarization_model == "gpt-4o"
    # Test semantic chunking defaults
    assert config_default.semantic_chunking_mode is False
    assert config_default.semantic_chunking_threshold == 0.8

    # Invalid case: zero max_tokens (ge=1)
    with pytest.raises(ValidationError):
        ProcessingConfig(max_tokens=0)
