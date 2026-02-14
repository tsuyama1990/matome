from domain_models.manifest import Chunk, DocumentTree, SummaryNode
from domain_models.types import NodeID
from matome.utils.store import DiskChunkStore


def _format_chunk(chunk: Chunk, depth: int) -> str:
    """Format a leaf chunk as a bullet point."""
    indent = "  " * depth
    # Limit chunk text length in export to avoid massive files?
    # Or keep full text? Usually summaries are short, chunks are long.
    # User might want full text.
    return f"{indent}- **Chunk {chunk.index}**: {chunk.text.strip()}"


def _format_summary(node: SummaryNode, depth: int) -> str:
    """Format a summary node as a heading."""
    heading_level = min(depth + 1, 6)
    heading = "#" * heading_level
    return f"{heading} {node.text.strip()}\n"


def _process_node(
    node_id: NodeID,
    depth: int,
    store: DiskChunkStore,
    lines: list[str],
    visited: set[NodeID],
) -> None:
    """Recursively process nodes for Markdown export."""
    if node_id in visited:
        return
    visited.add(node_id)

    node = store.get_node(node_id)
    if not node:
        return

    if isinstance(node, Chunk):
        lines.append(_format_chunk(node, depth))
        return

    if isinstance(node, SummaryNode):
        lines.append(_format_summary(node, depth))
        for child_idx in node.children_indices:
            _process_node(child_idx, depth + 1, store, lines, visited)


def export_to_markdown(tree: DocumentTree, store: DiskChunkStore) -> str:
    """
    Exports the DocumentTree to a Markdown string.

    The structure uses headings for summary levels and bullet points for leaf chunks.
    Root is H1 (#), children H2 (##), etc.

    Args:
        tree: The DocumentTree to export.
        store: DiskChunkStore to retrieve nodes (required as tree doesn't store them).

    Returns:
        A formatted Markdown string.
    """
    lines: list[str] = []
    visited: set[NodeID] = set()

    if tree.root_node:
        # Pre-load root node into visited to avoid cycle if root points to itself (shouldn't happen)
        # Actually root is in store too.
        _process_node(tree.root_node.id, 0, store, lines, visited)

    return "\n".join(lines)
