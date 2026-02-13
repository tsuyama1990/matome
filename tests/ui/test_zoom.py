from unittest.mock import MagicMock

import pytest
import param

from domain_models.data_schema import DIKWLevel, NodeMetadata
from domain_models.manifest import SummaryNode, Chunk
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.ui.session import InteractiveSession


@pytest.fixture
def mock_engine() -> MagicMock:
    engine = MagicMock(spec=InteractiveRaptorEngine)
    engine.get_nodes_by_level.return_value = []
    engine.get_children.return_value = []
    return engine

@pytest.fixture
def session(mock_engine: MagicMock) -> InteractiveSession:
    return InteractiveSession(engine=mock_engine)


def test_zoom_in(session: InteractiveSession, mock_engine: MagicMock) -> None:
    """Test zooming in updates context and breadcrumbs."""

    # Setup
    root = SummaryNode(
        id="root", text="Root", level=2, children_indices=["c1"],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )
    child = SummaryNode(
        id="c1", text="Child", level=1, children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
    )

    mock_engine.get_children.return_value = [child]

    # Action: Zoom into Root
    session.zoom_in(root)

    # Assertions
    assert session.view_context == root
    assert len(session.breadcrumbs) == 1
    assert session.breadcrumbs[0] == root
    assert session.current_level == DIKWLevel.KNOWLEDGE  # Should update level

    # Verify engine call to fetch children of root
    mock_engine.get_children.assert_called_with(root.id)
    assert session.available_nodes == [child]


def test_zoom_out(session: InteractiveSession, mock_engine: MagicMock) -> None:
    """Test zooming out restores previous state."""

    root = SummaryNode(
        id="root", text="Root", level=2, children_indices=["c1"],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )

    # Setup state: already zoomed in
    session.breadcrumbs = [root]
    session.view_context = root
    session.current_level = DIKWLevel.KNOWLEDGE

    # Action: Zoom out
    session.zoom_out()

    # Assertions
    assert session.view_context is None
    assert len(session.breadcrumbs) == 0
    assert session.current_level == DIKWLevel.WISDOM  # Should revert to root level

    # Verify engine call
    # It should fetch root level nodes (Wisdom)
    mock_engine.get_nodes_by_level.assert_called_with(DIKWLevel.WISDOM)


def test_zoom_in_leaf_node(session: InteractiveSession) -> None:
    """Test zooming in on a leaf node (empty children) is prevented."""

    leaf_summary = SummaryNode(
        id="leaf", text="Leaf", level=1, children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )

    session.zoom_in(leaf_summary)

    # Assert that zoom was prevented
    assert session.view_context is None
    assert "Cannot zoom into a leaf node" in session.status_message


def test_jump_to(session: InteractiveSession, mock_engine: MagicMock) -> None:
    """Test jumping to a specific breadcrumb."""

    n1 = SummaryNode(id="n1", text="1", level=3, children_indices=[], metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM))
    n2 = SummaryNode(id="n2", text="2", level=2, children_indices=[], metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE))
    n3 = SummaryNode(id="n3", text="3", level=1, children_indices=[], metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION))

    # Setup stack: n1 -> n2 -> n3 (currently viewing n3's children)
    session.breadcrumbs = [n1, n2, n3]
    session.view_context = n3
    session.current_level = DIKWLevel.DATA

    # Jump to n1
    session.jump_to(n1)

    assert session.view_context == n1
    assert session.breadcrumbs == [n1]
    assert session.current_level == DIKWLevel.KNOWLEDGE # Children of Wisdom are Knowledge

    # Verify engine call for n1 children
    mock_engine.get_children.assert_called_with(n1.id)


def test_get_source(session: InteractiveSession, mock_engine: MagicMock) -> None:
    """Test retrieving source chunks via session."""
    node = SummaryNode(id="s1", text="S", level=1, children_indices=[], metadata=NodeMetadata())
    chunks = [Chunk(index=1, text="C", start_char_idx=0, end_char_idx=1)]

    mock_engine.get_source_chunks.return_value = chunks

    result = session.get_source(node)

    assert result == chunks
    mock_engine.get_source_chunks.assert_called_with(node.id)
