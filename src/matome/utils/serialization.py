import json

from domain_models.manifest import Chunk, SummaryNode


def deserialize_node(
    node_id: str,
    node_type: str,
    content_json: str | None,
    embedding_json: str | None,
) -> Chunk | SummaryNode:
    """
    Helper to deserialize node data from database storage.

    Args:
        node_id: The ID of the node.
        node_type: The type of the node ('chunk' or 'summary').
        content_json: The JSON string containing the node's content.
        embedding_json: The JSON string containing the node's embedding (optional).

    Returns:
        The deserialized Chunk or SummaryNode object.

    Raises:
        ValueError: If content is missing, invalid JSON, or schema validation fails.
        TypeError: If the deserialized content is not a dictionary.
    """
    if not content_json:
        msg = f"Node {node_id} has empty content."
        raise ValueError(msg)

    try:
        embedding = json.loads(embedding_json) if embedding_json else None
        data = json.loads(content_json)
        if not isinstance(data, dict):
            msg = f"Node {node_id} content is not a JSON object."
            raise TypeError(msg)

        # Basic schema validation
        required_keys = {"text"}
        if node_type == "chunk":
            required_keys.update({"index", "start_char_idx", "end_char_idx"})
        elif node_type == "summary":
            required_keys.update({"id", "level", "children_indices", "metadata"})

        if not required_keys.issubset(data.keys()):
            msg = f"Node {node_id} missing required keys: {required_keys - data.keys()}"
            raise ValueError(msg)

    except json.JSONDecodeError as e:
        msg = f"Failed to decode JSON for node {node_id}: {e}"
        raise ValueError(msg) from e

    if embedding is not None:
        data["embedding"] = embedding

    if node_type == "chunk":
        return Chunk.model_validate(data)
    if node_type == "summary":
        return SummaryNode.model_validate(data)

    msg = f"Unknown node type: {node_type} for node {node_id}"
    raise ValueError(msg)
