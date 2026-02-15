import json

import pytest

from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from matome.utils.serialization import deserialize_node


def test_deserialize_chunk() -> None:
    chunk_data = {
        "index": 1,
        "text": "test text",
        "start_char_idx": 0,
        "end_char_idx": 9,
        "metadata": {}
    }
    content_json = json.dumps(chunk_data)
    embedding = [0.1, 0.2]
    embedding_json = json.dumps(embedding)

    result = deserialize_node("1", "chunk", content_json, embedding_json)

    assert isinstance(result, Chunk)
    assert result.index == 1
    assert result.text == "test text"
    assert result.embedding == embedding

def test_deserialize_summary() -> None:
    metadata_obj = NodeMetadata(dikw_level="data")
    summary_data = {
        "id": "node_1",
        "text": "summary text",
        "level": 1,
        "children_indices": [1, 2],
        "metadata": metadata_obj.model_dump()
    }
    content_json = json.dumps(summary_data)

    result = deserialize_node("node_1", "summary", content_json, None)

    assert isinstance(result, SummaryNode)
    assert result.id == "node_1"
    assert result.embedding is None

def test_deserialize_invalid_json() -> None:
    with pytest.raises(ValueError, match="Failed to decode JSON"):
        deserialize_node("1", "chunk", "{invalid json", None)

def test_deserialize_empty_content() -> None:
    with pytest.raises(ValueError, match="empty content"):
        deserialize_node("1", "chunk", "", None)

def test_deserialize_missing_keys() -> None:
    data = {"text": "incomplete"}
    content_json = json.dumps(data)
    with pytest.raises(ValueError, match="Schema validation failed"):
        deserialize_node("1", "chunk", content_json, None)

def test_deserialize_unknown_type() -> None:
    chunk_data = {
        "index": 1,
        "text": "test text",
        "start_char_idx": 0,
        "end_char_idx": 9,
        "metadata": {}
    }
    content_json = json.dumps(chunk_data)
    with pytest.raises(ValueError, match="Unknown node type"):
        deserialize_node("1", "unknown", content_json, None)
