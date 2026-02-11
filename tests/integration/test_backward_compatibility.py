import pytest
from domain_models.manifest import SummaryNode
from domain_models.metadata import DIKWLevel, NodeMetadata

def test_load_legacy_summary_node() -> None:
    legacy_json = """
    {
        "id": "123",
        "text": "Old summary",
        "level": 1,
        "children_indices": [0, 1],
        "metadata": {
            "source": "old_file.txt"
        }
    }
    """
    node = SummaryNode.model_validate_json(legacy_json)

    # Check DIKW Level Default
    assert isinstance(node.metadata, NodeMetadata)
    assert node.metadata.dikw_level == DIKWLevel.DATA

    # Check Extra Field Preservation
    # Pydantic V2 allows accessing extra fields via dynamic attribute if configured
    # We check if 'source' is in the attributes
    assert getattr(node.metadata, "source") == "old_file.txt"
    # Also check dict access if model_dump is used
    dump = node.metadata.model_dump(exclude_unset=True)
    assert dump["source"] == "old_file.txt"
