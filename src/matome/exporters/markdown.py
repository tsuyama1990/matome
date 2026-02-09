from domain_models.manifest import Chunk, DocumentTree


def _process_node(
    node_id: str | int,
    is_chunk: bool,
    depth: int,
    tree: DocumentTree,
    chunk_map: dict[int, Chunk],
    lines: list[str],
) -> None:
    """Recursively process nodes for Markdown export."""
    if is_chunk:
        if isinstance(node_id, int):
            chunk = chunk_map.get(node_id)
            if chunk:
                # Leaf node: Bullet point
                indent = "  " * depth
                lines.append(f"{indent}- **Chunk {chunk.index}**: {chunk.text.strip()}")
        return

    # It's a SummaryNode
    if isinstance(node_id, str):
        node = tree.root_node if node_id == tree.root_node.id else tree.all_nodes.get(node_id)

        if not node:
            return

        # Heading
        heading_level = min(depth + 1, 6)
        heading = "#" * heading_level

        lines.append(f"{heading} {node.text.strip()}")
        lines.append("")

        # Process Children
        for child_idx in node.children_indices:
            if isinstance(child_idx, str):
                # Child is SummaryNode
                _process_node(child_idx, False, depth + 1, tree, chunk_map, lines)
            elif isinstance(child_idx, int):
                # Child is Chunk
                _process_node(child_idx, True, depth + 1, tree, chunk_map, lines)


def export_to_markdown(tree: DocumentTree) -> str:
    """
    Exports the DocumentTree to a Markdown string.

    The structure uses headings for summary levels and bullet points for leaf chunks.
    Root is H1 (#), children H2 (##), etc.

    Args:
        tree: The DocumentTree to export.

    Returns:
        A formatted Markdown string.
    """
    lines: list[str] = []
    chunk_map: dict[int, Chunk] = {c.index: c for c in tree.leaf_chunks}

    if tree.root_node:
        _process_node(tree.root_node.id, False, 0, tree, chunk_map, lines)

    return "\n".join(lines)
