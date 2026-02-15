import pytest
from pydantic import ValidationError

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster, DocumentTree, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel


def test_chunk_validation() -> None:
    # Valid chunk
    c = Chunk(index=0, text="valid", start_char_idx=0, end_char_idx=5)
    assert c.text == "valid"

    # Invalid range - start > end
    with pytest.raises(ValidationError):
        Chunk(index=0, text="valid", start_char_idx=10, end_char_idx=5)

    # Empty text
    with pytest.raises(ValidationError):
        Chunk(index=0, text="", start_char_idx=0, end_char_idx=0)

    # Invalid embedding
    with pytest.raises(ValidationError):
        Chunk(index=0, text="valid", start_char_idx=0, end_char_idx=5, embedding=[])


def test_node_metadata_defaults() -> None:
    meta = NodeMetadata()
    assert meta.dikw_level == DIKWLevel.DATA
    assert not meta.is_user_edited
    assert meta.refinement_history == []


def test_summary_node_validation() -> None:
    meta = NodeMetadata(dikw_level=DIKWLevel.INFORMATION)

    # Valid
    node = SummaryNode(
        id="node_1",
        text="Summary",
        level=1,
        children_indices=["0", "1"],
        metadata=meta,
    )
    assert node.level == 1

    # Invalid level (must be >= 1)
    with pytest.raises(ValidationError):
        SummaryNode(
            id="node_1",
            text="Summary",
            level=0,
            children_indices=["0"],
            metadata=meta,
        )


def test_cluster_validation() -> None:
    # Valid
    c = Cluster(id=0, level=0, node_indices=[0, 1])
    assert c.id == 0

    # Invalid level
    with pytest.raises(ValidationError):
        Cluster(id=0, level=-1, node_indices=[0])


def test_document_tree_structure() -> None:
    meta = NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    root = SummaryNode(
        id="root",
        text="Root",
        level=2,
        children_indices=["c1"],
        metadata=meta,
    )

    tree = DocumentTree(
        root_node=root,
        leaf_chunk_ids=[0, 1, 2],
        metadata={"version": "1.0"}
    )
    assert tree.root_node.id == "root"
    assert len(tree.leaf_chunk_ids) == 3


def test_config_validation() -> None:
    # Valid defaults
    config = ProcessingConfig()
    assert config.max_tokens > 0

    # Invalid max_tokens
    with pytest.raises(ValidationError):
        ProcessingConfig(max_tokens=0)

    # Invalid semantic chunking threshold
    with pytest.raises(ValidationError):
        ProcessingConfig(semantic_chunking_mode=True, semantic_chunking_threshold=1.5)

    # Invalid model name
    with pytest.raises(ValidationError):
        ProcessingConfig(embedding_model="invalid/model!name")

    # Inconsistent tokens
    with pytest.raises(ValidationError):
        ProcessingConfig(max_tokens=10, max_summary_tokens=20)
