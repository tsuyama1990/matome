from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.utils.store import DiskChunkStore


def test_get_max_level(tmp_path):
    store = DiskChunkStore(db_path=tmp_path / "test.db")

    # Empty store
    assert store.get_max_level() == 0

    # Add level 1
    node1 = SummaryNode(
        id="1", text="text", level=1, children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )
    store.add_summary(node1)
    assert store.get_max_level() == 1

    # Add level 3
    node3 = SummaryNode(
        id="3", text="text", level=3, children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )
    store.add_summary(node3)
    assert store.get_max_level() == 3

    store.close()
