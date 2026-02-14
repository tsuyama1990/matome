from unittest.mock import MagicMock

from domain_models.manifest import Chunk, DocumentTree, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.exporters.markdown import export_to_markdown


def test_export_to_markdown() -> None:
    """Test exporting DocumentTree to Markdown."""
    # Setup tree
    # Root (Level 2)
    #  - Summary L1 (Level 1)
    #     - Chunk 0
    #     - Chunk 1

    chunk0 = Chunk(index=0, text="Chunk 0 text", start_char_idx=0, end_char_idx=10)
    chunk1 = Chunk(index=1, text="Chunk 1 text", start_char_idx=10, end_char_idx=20)

    summary_l1 = SummaryNode(
        id="s1",
        text="Summary L1 text",
        level=1,
        children_indices=[0, 1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )

    root = SummaryNode(
        id="root",
        text="Root text",
        level=2,
        children_indices=["s1"],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )

    tree = DocumentTree(
        root_node=root, leaf_chunk_ids=[0, 1]
    )

    # Mock store
    store = MagicMock()

    def get_node_side_effect(node_id: int | str) -> Chunk | SummaryNode | None:
        nodes: dict[int | str, Chunk | SummaryNode] = {0: chunk0, 1: chunk1, "s1": summary_l1, "root": root}
        return nodes.get(node_id)

    store.get_node.side_effect = get_node_side_effect

    # Export
    md = export_to_markdown(tree, store)

    # Verify basics
    assert isinstance(md, str)
    assert len(md) > 0

    # Check structure
    lines = md.splitlines()

    # Root should be h1 (#)
    assert any(line.strip() == "# Root text" for line in lines)

    # Summary L1 should be h2 (##) because it is depth 1
    assert any(line.strip() == "## Summary L1 text" for line in lines)

    # Chunks should be bullet points
    # Chunk 0
    chunk0_line = next((line for line in lines if "Chunk 0 text" in line), None)
    assert chunk0_line is not None
    assert chunk0_line.strip().startswith("- **Chunk 0**:")

    # Chunk 1
    chunk1_line = next((line for line in lines if "Chunk 1 text" in line), None)
    assert chunk1_line is not None
    assert chunk1_line.strip().startswith("- **Chunk 1**:")
