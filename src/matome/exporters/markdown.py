from domain_models.manifest import Chunk, DocumentTree, SummaryNode
from matome.utils.store import DiskChunkStore


def _format_chunk(chunk: Chunk, depth: int) -> str:
    """Format a leaf chunk as a bullet point."""
    indent = "  " * depth
    return f"{indent}- **Chunk {chunk.index}**: {chunk.text.strip()}"


def _format_summary(node: SummaryNode, depth: int) -> tuple[str, str]:
    """Format a summary node as a heading."""
    heading_level = min(depth + 1, 6)
    heading = "#" * heading_level
    return f"{heading} {node.text.strip()}", ""


def _get_chunk_for_export(
    node_id: int, chunk_map: dict[int, Chunk], store: DiskChunkStore | None
) -> Chunk | None:
    """Retrieve chunk from map or store."""
    chunk = chunk_map.get(node_id)
    if chunk:
        return chunk
    if store:
        node = store.get_node(node_id)
        if isinstance(node, Chunk):
            return node
    return None


def _get_summary_for_export(
    node_id: str, tree: DocumentTree, store: DiskChunkStore | None
) -> SummaryNode | None:
    """Retrieve summary from tree or store."""
    if node_id == tree.root_node.id:
        return tree.root_node
    node = tree.all_nodes.get(node_id)
    if node:
        return node
    if store:
        fetched = store.get_node(node_id)
        if isinstance(fetched, SummaryNode):
            return fetched
    return None


def _process_node(
    node_id: str | int,
    is_chunk: bool,
    depth: int,
    tree: DocumentTree,
    chunk_map: dict[int, Chunk],
    lines: list[str],
    store: DiskChunkStore | None = None,
) -> None:
    """Recursively process nodes for Markdown export."""
    if is_chunk:
        if isinstance(node_id, int):
            chunk = _get_chunk_for_export(node_id, chunk_map, store)
            if chunk:
                lines.append(_format_chunk(chunk, depth))
        return

    # It's a SummaryNode
    if isinstance(node_id, str):
        node = _get_summary_for_export(node_id, tree, store)
        if not node:
            return

        # Heading
        heading, empty_line = _format_summary(node, depth)
        lines.append(heading)
        lines.append(empty_line)

        # Process Children
        for child_idx in node.children_indices:
            if isinstance(child_idx, str):
                _process_node(child_idx, False, depth + 1, tree, chunk_map, lines, store)
            elif isinstance(child_idx, int):
                _process_node(child_idx, True, depth + 1, tree, chunk_map, lines, store)


def export_to_markdown(tree: DocumentTree, store: DiskChunkStore | None = None) -> str:
    """
    Exports the DocumentTree to a Markdown string.

    The structure uses headings for summary levels and bullet points for leaf chunks.
    Root is H1 (#), children H2 (##), etc.

    Args:
        tree: The DocumentTree to export.
        store: Optional DiskChunkStore to retrieve leaf chunk text.

    Returns:
        A formatted Markdown string.
    """
    lines: list[str] = []
    chunk_map: dict[int, Chunk] = {}

    if store and tree.leaf_chunk_ids:
        for chunk_id in tree.leaf_chunk_ids:
            node = store.get_node(chunk_id)
            if isinstance(node, Chunk):
                chunk_map[node.index] = node

    if tree.root_node:
        _process_node(tree.root_node.id, False, 0, tree, chunk_map, lines, store)

    return "\n".join(lines)
