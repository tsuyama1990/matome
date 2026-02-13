from unittest.mock import MagicMock

import pytest

from domain_models.data_schema import NodeMetadata
from domain_models.manifest import SummaryNode
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.ui.canvas import MatomeCanvas
from matome.ui.session import InteractiveSession


@pytest.fixture
def mock_session() -> InteractiveSession:
    engine = MagicMock(spec=InteractiveRaptorEngine)
    engine.get_nodes_by_level.return_value = []
    session = InteractiveSession(engine=engine)
    # Mock some data
    session.available_nodes = [
        SummaryNode(id="s1", text="Node 1", level=1, children_indices=[], metadata=NodeMetadata())
    ]
    return session

def test_canvas_initialization(mock_session: InteractiveSession) -> None:
    """Test that MatomeCanvas initializes without error."""
    canvas = MatomeCanvas(session=mock_session)
    assert canvas.session == mock_session

def test_canvas_layout(mock_session: InteractiveSession) -> None:
    """Test that the layout can be generated."""
    canvas = MatomeCanvas(session=mock_session)
    # This might fail if panel relies on a server context or extension, but usually template instantiation works.
    try:
        layout = canvas.layout
        assert layout is not None
        # Check title
        assert "Matome 2.0" in layout.title
    except Exception as e:
        pytest.fail(f"Failed to generate layout: {e}")

def test_components_exist(mock_session: InteractiveSession) -> None:
    """Test that main components are created."""
    canvas = MatomeCanvas(session=mock_session)

    # We can inspect internal methods or properties if we expose them
    # Assuming standard implementation
    assert canvas.sidebar is not None
    assert canvas.main_area is not None
