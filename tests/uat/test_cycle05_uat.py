import json
from pathlib import Path

import pytest

from domain_models.manifest import Chunk, DocumentTree, SummaryNode
from matome.exporters.obsidian import ObsidianCanvasExporter


@pytest.fixture
def uat_tree() -> DocumentTree:
    """
    Create a complex tree for UAT:
    Root
      |-- Cluster A (Summary A)
      |     |-- Chunk 1
      |     |-- Chunk 2
      |-- Cluster B (Summary B)
            |-- Chunk 3
    """
    c1 = Chunk(index=1, text="Chunk 1", start_char_idx=0, end_char_idx=5)
    c2 = Chunk(index=2, text="Chunk 2", start_char_idx=6, end_char_idx=10)
    c3 = Chunk(index=3, text="Chunk 3", start_char_idx=11, end_char_idx=15)

    node_a = SummaryNode(
        id="summary_a",
        text="Summary A",
        level=1,
        children_indices=[1, 2]
    )
    node_b = SummaryNode(
        id="summary_b",
        text="Summary B",
        level=1,
        children_indices=[3]
    )
    root = SummaryNode(
        id="root",
        text="Root Summary",
        level=2,
        children_indices=["summary_a", "summary_b"]
    )

    return DocumentTree(
        root_node=root,
        all_nodes={"root": root, "summary_a": node_a, "summary_b": node_b},
        leaf_chunk_ids=[c1.index, c2.index, c3.index]
    )


def test_scenario_14_canvas_generation(uat_tree: DocumentTree, tmp_path: Path) -> None:
    """
    Scenario 14: Canvas File Generation (Priority: High)
    Goal: Ensure the exported .canvas file is valid JSON and importable by Obsidian.
    """
    exporter = ObsidianCanvasExporter()
    output_path = tmp_path / "scenario_14.canvas"

    exporter.export(uat_tree, output_path)

    assert output_path.exists()

    with output_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert "nodes" in data
    assert "edges" in data

    # Check node count: Root + A + B + 3 chunks = 6 nodes
    assert len(data["nodes"]) == 6
    # Check edge count: Root->A, Root->B, A->1, A->2, B->3 = 5 edges
    assert len(data["edges"]) == 5


def test_scenario_15_visual_hierarchy(uat_tree: DocumentTree) -> None:
    """
    Scenario 15: Visual Hierarchy Check (Priority: Medium)
    Goal: Ensure the visual layout reflects the logical structure.
    Expected Outcome:
        * Root is at the top.
        * A and B are below Root.
        * a1, a2 are below A; b1 is below B.
    """
    exporter = ObsidianCanvasExporter()
    canvas = exporter.generate_canvas_data(uat_tree)

    # Helper to get node by ID
    from matome.exporters.obsidian import CanvasNode

    def get_node(nid: str) -> CanvasNode | None:
        return next((n for n in canvas.nodes if n.id == nid), None)

    root = get_node("root")
    node_a = get_node("summary_a")
    node_b = get_node("summary_b")
    chunk_1 = get_node("chunk_1")
    chunk_2 = get_node("chunk_2")
    chunk_3 = get_node("chunk_3")

    assert root is not None
    assert node_a is not None
    assert node_b is not None
    assert chunk_1 is not None
    assert chunk_2 is not None
    assert chunk_3 is not None

    # 1. Root is at the top
    assert root.y == 0

    # 2. A and B are below Root
    assert node_a.y > root.y
    assert node_b.y > root.y

    # 3. Chunks are below their parents
    assert chunk_1.y > node_a.y
    assert chunk_2.y > node_a.y
    assert chunk_3.y > node_b.y

    # 4. A and B should be horizontally separated
    assert node_a.x != node_b.x

    # 5. Edges should exist
    edges_from_root = [e for e in canvas.edges if e.from_node == "root"]
    assert len(edges_from_root) == 2

    edges_from_a = [e for e in canvas.edges if e.from_node == "summary_a"]
    assert len(edges_from_a) == 2

    edges_from_b = [e for e in canvas.edges if e.from_node == "summary_b"]
    assert len(edges_from_b) == 1
