from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.utils.store import DiskChunkStore
from matome.utils.traversal import traverse_source_chunks


@pytest.fixture
def mock_store() -> MagicMock:
    return MagicMock(spec=DiskChunkStore)


def create_summary(
    node_id: str, children: list[str | int], level: int = 1
) -> SummaryNode:
    return SummaryNode(
        id=node_id,
        text=f"Summary {node_id}",
        level=level,
        children_indices=children,
        metadata=NodeMetadata(dikw_level=DIKWLevel.DATA),
    )


def create_chunk(index: int) -> Chunk:
    return Chunk(
        index=index,
        text=f"Chunk {index}",
        start_char_idx=0,
        end_char_idx=10,
    )


def test_traverse_simple_tree(mock_store: MagicMock) -> None:
    # Root -> [Chunk 1, Chunk 2]
    root = create_summary("root", [1, 2])
    c1 = create_chunk(1)
    c2 = create_chunk(2)

    def get_nodes_side_effect(ids: list[str | int]) -> Iterator[Chunk | SummaryNode]:
        for node_id in ids:
            if node_id == 1:
                yield c1
            elif node_id == 2:
                yield c2

    mock_store.get_nodes.side_effect = get_nodes_side_effect

    chunks = list(traverse_source_chunks(mock_store, root))

    assert len(chunks) == 2
    assert chunks[0].index == 1
    assert chunks[1].index == 2
    mock_store.get_nodes.assert_called()


def test_traverse_nested_tree(mock_store: MagicMock) -> None:
    # Root -> [Mid 1, Mid 2]
    # Mid 1 -> [Chunk 1]
    # Mid 2 -> [Chunk 2]
    root = create_summary("root", ["mid1", "mid2"], level=2)
    mid1 = create_summary("mid1", [1], level=1)
    mid2 = create_summary("mid2", [2], level=1)
    c1 = create_chunk(1)
    c2 = create_chunk(2)

    def get_nodes_side_effect(ids: list[str | int]) -> Iterator[Chunk | SummaryNode]:
        for node_id in ids:
            if node_id == "mid1":
                yield mid1
            elif node_id == "mid2":
                yield mid2
            elif node_id == 1:
                yield c1
            elif node_id == 2:
                yield c2

    mock_store.get_nodes.side_effect = get_nodes_side_effect

    chunks = list(traverse_source_chunks(mock_store, root))

    assert len(chunks) == 2
    assert {c.index for c in chunks} == {1, 2}


def test_traverse_limit(mock_store: MagicMock) -> None:
    root = create_summary("root", [1, 2, 3])
    c1 = create_chunk(1)
    c2 = create_chunk(2)
    c3 = create_chunk(3)

    mock_store.get_nodes.return_value = iter([c1, c2, c3])

    chunks = list(traverse_source_chunks(mock_store, root, limit=2))

    assert len(chunks) == 2


def test_traverse_cycle_prevention(mock_store: MagicMock) -> None:
    # Root -> [Mid 1]
    # Mid 1 -> [Root] (Cycle)
    # Mid 1 -> [Chunk 1]
    root = create_summary("root", ["mid1"], level=2)
    mid1 = create_summary("mid1", ["root", 1], level=1)
    c1 = create_chunk(1)

    store_map: dict[str | int, Chunk | SummaryNode] = {
        "mid1": mid1,
        "root": root,
        1: c1
    }

    def get_nodes_side_effect(ids: list[str | int]) -> Iterator[Chunk | SummaryNode]:
        for node_id in ids:
            if node_id in store_map:
                yield store_map[node_id]

    mock_store.get_nodes.side_effect = get_nodes_side_effect

    chunks = list(traverse_source_chunks(mock_store, root))

    assert len(chunks) == 1
    assert chunks[0].index == 1
