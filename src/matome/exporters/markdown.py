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


def _process_chunk_node(
    node_id: int, depth: int, store: DiskChunkStore | None, lines: list[str]
) -> None:
    """Process a chunk node."""
    chunk: Chunk | None = None
    if store:
        node = store.get_node(node_id)
        if isinstance(node, Chunk):
            chunk = node

    if chunk:
        lines.append(_format_chunk(chunk, depth))


def _process_summary_node(
    node_id: str, depth: int, root_node: SummaryNode, store: DiskChunkStore | None, lines: list[str]
) -> None:
    """Process a summary node."""
    node: SummaryNode | None = None

    if node_id == root_node.id:
        node = root_node
    elif store:
        stored_node = store.get_node(node_id)
        if isinstance(stored_node, SummaryNode):
            node = stored_node

    if not node:
        return

    # Heading
    heading, empty_line = _format_summary(node, depth)
    lines.append(heading)
    lines.append(empty_line)

    # Process Children
    for child_idx in node.children_indices:
        if isinstance(child_idx, str):
            _process_summary_node(child_idx, depth + 1, root_node, store, lines)
        elif isinstance(child_idx, int):
            _process_chunk_node(child_idx, depth + 1, store, lines)


def _process_node(
    node_id: str | int,
    is_chunk: bool,
    depth: int,
    tree: DocumentTree,
    store: DiskChunkStore | None,
    lines: list[str],
) -> None:
    """Recursively process nodes for Markdown export."""
    if is_chunk and isinstance(node_id, int):
        _process_chunk_node(node_id, depth, store, lines)
    elif isinstance(node_id, str):
        _process_summary_node(node_id, depth, tree.root_node, store, lines)


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

    if tree.root_node:
        _process_node(tree.root_node.id, False, 0, tree, store, lines)

    return "\n".join(lines)
