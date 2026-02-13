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


def _fetch_summary_node(
    node_id: str, tree: DocumentTree, store: DiskChunkStore | None
) -> SummaryNode | None:
    """Retrieve summary node from tree root or store."""
    if node_id == tree.root_node.id:
        return tree.root_node
    if store:
        stored_node = store.get_node(node_id)
        if isinstance(stored_node, SummaryNode):
            return stored_node
    return None


def _process_summary_children(
    node: SummaryNode, depth: int, stack: list[tuple[str | int, bool, int]]
) -> None:
    """Push summary children to stack in reverse order."""
    for child_idx in reversed(node.children_indices):
        if isinstance(child_idx, str):
            stack.append((child_idx, False, depth + 1))
        elif isinstance(child_idx, int):
            stack.append((child_idx, True, depth + 1))


def _process_node_iterative(
    start_node_id: str | int,
    start_depth: int,
    tree: DocumentTree,
    store: DiskChunkStore | None,
    lines: list[str],
) -> None:
    """
    Iterative implementation of node processing to avoid stack overflow.
    """
    # Stack elements: (node_id, is_chunk, depth)
    is_chunk_start = isinstance(start_node_id, int)
    stack: list[tuple[str | int, bool, int]] = [(start_node_id, is_chunk_start, start_depth)]

    while stack:
        curr_id, is_chunk, depth = stack.pop()

        if is_chunk:
            # Type guard for mypy
            if isinstance(curr_id, int):
                _process_chunk_node(curr_id, depth, store, lines)
            continue

        # Summary Node processing
        if isinstance(curr_id, str):
            node: SummaryNode | None = None
            if curr_id == tree.root_node.id:
                node = tree.root_node
            elif store:
                stored_node = store.get_node(curr_id)
                if isinstance(stored_node, SummaryNode):
                    node = stored_node

            if not node:
                continue

            heading, empty_line = _format_summary(node, depth)
            lines.append(heading)
            lines.append(empty_line)

            _process_summary_children(node, depth, stack)


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
        _process_node_iterative(tree.root_node.id, 0, tree, store, lines)

    return "\n".join(lines)
