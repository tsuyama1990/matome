from domain_models.manifest import SummaryNode
from domain_models.metadata import DIKWLevel, NodeMetadata


def test_loading_legacy_json() -> None:
    """Test loading legacy JSON where metadata was a dict."""
    # Mimic old JSON structure where metadata was a dict
    legacy_json = """
    {
        "id": "node_legacy",
        "text": "Old Summary",
        "level": 1,
        "children_indices": [0, 1],
        "metadata": {
            "source": "old_db",
            "timestamp": 12345
        }
    }
    """
    node = SummaryNode.model_validate_json(legacy_json)

    # Check that metadata is upgraded to NodeMetadata
    assert isinstance(node.metadata, NodeMetadata)
    # Check defaults
    assert node.metadata.dikw_level == DIKWLevel.DATA
    assert node.metadata.is_user_edited is False
    # Check preserved extra fields
    assert node.metadata.source == "old_db"  # type: ignore
    assert node.metadata.timestamp == 12345  # type: ignore


def test_loading_legacy_without_metadata() -> None:
    """Test loading JSON without metadata field."""
    legacy_json = """
    {
        "id": "node_empty",
        "text": "No Metadata",
        "level": 1,
        "children_indices": [0]
    }
    """
    node = SummaryNode.model_validate_json(legacy_json)
    assert isinstance(node.metadata, NodeMetadata)
    assert node.metadata.dikw_level == DIKWLevel.DATA
