# This will fail until implementation
from domain_models.manifest import Chunk, DocumentTree, SummaryNode
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
        children_indices=[0, 1]
    )

    root = SummaryNode(
        id="root",
        text="Root text",
        level=2,
        children_indices=["s1"]
    )

    tree = DocumentTree(
        root_node=root,
        all_nodes={"s1": summary_l1, "root": root},
        leaf_chunks=[chunk0, chunk1]
    )

    # Export
    md = export_to_markdown(tree)

    # Verify basics
    assert isinstance(md, str)
    assert len(md) > 0

    # Check structure
    # Root should be h1 or top level
    assert "# Root text" in md or "Root text" in md

    # Summary L1 should be nested or listed
    assert "Summary L1 text" in md

    # Chunks should be present
    assert "Chunk 0 text" in md
    assert "Chunk 1 text" in md
