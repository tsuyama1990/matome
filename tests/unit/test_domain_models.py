import pytest
from pydantic import ValidationError

from domain_models.config import (
    ChunkingConfig,
    ProcessingConfig,
)
from domain_models.manifest import Chunk, Cluster, Document, SummaryNode, Tree


def test_document_validation() -> None:
    """Test valid and invalid Document creation."""
    # Valid
    doc = Document(content="hello", metadata={"source": "test"})
    assert doc.content == "hello"
    assert doc.metadata == {"source": "test"}

    # Invalid case: missing content
    with pytest.raises(ValidationError):
        Document(metadata={}) # type: ignore[call-arg]


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

    # Invalid case: embedding integrity
    with pytest.raises(ValidationError):
        Chunk(
            index=0,
            text="text",
            start_char_idx=0,
            end_char_idx=4,
            embedding=[] # Empty embedding not allowed
        )

    # Helper method
    c = Chunk(index=0, text="A", start_char_idx=0, end_char_idx=1)
    with pytest.raises(ValueError, match="requires an embedding"):
        c.require_embedding()


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


def test_tree_validation() -> None:
    """Test Tree structure validation."""
    # Setup components
    chunk1 = Chunk(index=0, text="A", start_char_idx=0, end_char_idx=1)
    chunk2 = Chunk(index=1, text="B", start_char_idx=1, end_char_idx=2)
    summary = SummaryNode(
        id="s1",
        text="AB",
        level=1,
        children_indices=[0, 1]
    )

    # Valid Tree
    tree = Tree(
        chunks=[chunk1, chunk2],
        summaries=[summary]
    )
    assert len(tree.chunks) == 2
    assert len(tree.summaries) == 1


def test_config_validation() -> None:
    """Test ProcessingConfig validation."""
    # Valid
    config = ProcessingConfig(chunking=ChunkingConfig(max_tokens=100, overlap=10))
    assert config.chunking.max_tokens == 100

    # Test defaults
    config_default = ProcessingConfig.default()
    assert config_default.clustering.algorithm == "gmm"
    assert config_default.summarization.model_name == "gpt-4o"

    # Invalid case: zero max_tokens (ge=1)
    with pytest.raises(ValidationError):
        ChunkingConfig(max_tokens=0)
