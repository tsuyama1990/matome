from collections.abc import Iterator

from domain_models.manifest import Chunk, DocumentTree, SummaryNode
from domain_models.types import NodeID
from matome.utils.store import DiskChunkStore


def _format_chunk(chunk: Chunk, depth: int) -> str:
    """Format a leaf chunk as a bullet point."""
    indent = "  " * depth
    # Add newline for consistency
    return f"{indent}- **Chunk {chunk.index}**: {chunk.text.strip()}\n"


def _format_summary(node: SummaryNode, depth: int) -> str:
    """Format a summary node as a heading."""
    heading_level = min(depth + 1, 6)
    heading = "#" * heading_level
    return f"{heading} {node.text.strip()}\n"


def _stream_nodes(
    root_id: NodeID,
    store: DiskChunkStore,
) -> Iterator[tuple[NodeID, int]]:
    """
    Iteratively yield nodes in DFS order with depth.
    """
    # Stack stores (node_id, depth)
    stack: list[tuple[NodeID, int]] = [(root_id, 0)]
    visited: set[NodeID] = set()

    while stack:
        curr_id, depth = stack.pop()

        if curr_id in visited:
            continue
        visited.add(curr_id)

        node = store.get_node(curr_id)
        if not node:
            continue

        yield curr_id, depth

        if isinstance(node, SummaryNode):
            # Push children in reverse order to preserve left-to-right traversal
            for child_idx in reversed(node.children_indices):
                stack.append((child_idx, depth + 1))


def stream_markdown(tree: DocumentTree, store: DiskChunkStore) -> Iterator[str]:
    """
    Generates Markdown lines iteratively.
    """
    if not tree.root_node:
        return

    root_id = tree.root_node.id if isinstance(tree.root_node, SummaryNode) else tree.root_node.index

    for node_id, depth in _stream_nodes(root_id, store):
        node = store.get_node(node_id)
        if not node:
            continue

        if isinstance(node, Chunk):
            yield _format_chunk(node, depth)
        elif isinstance(node, SummaryNode):
            yield _format_summary(node, depth)


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
    return "".join(stream_markdown(tree, store))
