import json
from pathlib import Path

from sqlalchemy import text

from domain_models.manifest import SummaryNode
from domain_models.metadata import DIKWLevel, NodeMetadata
from matome.utils.store import DiskChunkStore


def test_store_metadata_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "test_store.db"
    store = DiskChunkStore(db_path)

    # Create a node with metadata
    meta = NodeMetadata(dikw_level=DIKWLevel.WISDOM, is_user_edited=True)
    node = SummaryNode(
        id="node1",
        text="summary",
        level=1,
        children_indices=["c1"],
        metadata=meta,
    )

    store.add_summary(node)

    # Retrieve the node
    retrieved = store.get_node("node1")
    assert retrieved is not None
    assert isinstance(retrieved, SummaryNode)
    assert retrieved.metadata.dikw_level == DIKWLevel.WISDOM
    assert retrieved.metadata.is_user_edited is True

    store.close()


def test_store_metadata_backward_compatibility(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_test.db"
    store = DiskChunkStore(db_path)

    # Manually insert a legacy node (no DIKW level) directly into DB to simulate old data
    # But DiskChunkStore encapsulates DB access.
    # I can use store.engine to execute raw SQL.

    with store.engine.begin() as conn:
        # Create a JSON content that matches old schema (metadata is a dict)
        content_json = json.dumps(
            {
                "id": "legacy1",
                "text": "legacy summary",
                "level": 1,
                "children_indices": ["c2"],
                "metadata": {"cluster_id": 99},
            }
        )
        conn.execute(
            text(
                "INSERT INTO nodes (id, type, content, embedding) VALUES ('legacy1', 'summary', :content, NULL)"
            ),
            {"content": content_json},
        )

    # Retrieve using new class
    retrieved = store.get_node("legacy1")
    assert retrieved is not None
    assert isinstance(retrieved, SummaryNode)
    assert retrieved.metadata.dikw_level is None
    # Check that extra field is preserved (NodeMetadata has extra='allow')
    # But 'cluster_id' is now a defined field in NodeMetadata
    assert retrieved.metadata.cluster_id == 99

    store.close()
