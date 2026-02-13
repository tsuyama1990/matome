import pytest
from unittest.mock import MagicMock
from matome.ui.session import InteractiveSession
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from domain_models.manifest import SummaryNode
from domain_models.data_schema import NodeMetadata, DIKWLevel

@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=InteractiveRaptorEngine)
    # Default behavior for get_nodes_by_level
    engine.get_nodes_by_level.return_value = []
    return engine

def test_initialization(mock_engine):
    session = InteractiveSession(engine=mock_engine)
    assert session.current_level == DIKWLevel.WISDOM
    assert session.selected_node is None
    assert session.is_refining is False
    assert session.refinement_instruction == ""
    assert "Loaded 0 wisdom nodes" in session.status_message

    # Check that it fetched initial nodes
    mock_engine.get_nodes_by_level.assert_called_with(DIKWLevel.WISDOM)

def test_level_change_updates_nodes(mock_engine):
    session = InteractiveSession(engine=mock_engine)

    # Setup mock for Knowledge level
    mock_nodes = [MagicMock(spec=SummaryNode)]
    mock_engine.get_nodes_by_level.return_value = mock_nodes

    # Change level
    session.current_level = DIKWLevel.KNOWLEDGE

    # Verify engine call
    mock_engine.get_nodes_by_level.assert_called_with(DIKWLevel.KNOWLEDGE)
    assert session.available_nodes == mock_nodes
    # Should clear selection on level change? Usually yes.
    assert session.selected_node is None

def test_select_node(mock_engine):
    session = InteractiveSession(engine=mock_engine)
    node = SummaryNode(id="s1", text="Text", level=1, children_indices=[], metadata=NodeMetadata())
    mock_engine.get_node.return_value = node

    session.select_node("s1")

    assert session.selected_node == node
    assert "s1" in session.status_message
    mock_engine.get_node.assert_called_with("s1")

def test_submit_refinement_success(mock_engine):
    session = InteractiveSession(engine=mock_engine)
    node = SummaryNode(id="s1", text="Old", level=1, children_indices=[], metadata=NodeMetadata())
    session.selected_node = node
    session.refinement_instruction = "Improve"

    refined_node = SummaryNode(id="s1", text="New", level=1, children_indices=[], metadata=NodeMetadata())
    mock_engine.refine_node.return_value = refined_node

    session.submit_refinement()

    mock_engine.refine_node.assert_called_with("s1", "Improve")
    assert session.selected_node == refined_node
    assert session.refinement_instruction == ""
    assert session.is_refining is False
    assert "Refinement complete" in session.status_message

def test_submit_refinement_no_selection(mock_engine):
    session = InteractiveSession(engine=mock_engine)
    session.selected_node = None
    session.refinement_instruction = "Improve"

    session.submit_refinement()

    mock_engine.refine_node.assert_not_called()
    assert "No node selected" in session.status_message

def test_submit_refinement_empty_instruction(mock_engine):
    session = InteractiveSession(engine=mock_engine)
    node = SummaryNode(id="s1", text="Old", level=1, children_indices=[], metadata=NodeMetadata())
    session.selected_node = node
    session.refinement_instruction = ""

    session.submit_refinement()

    mock_engine.refine_node.assert_not_called()
    assert "Please enter" in session.status_message
