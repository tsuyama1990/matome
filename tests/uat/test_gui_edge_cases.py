from unittest.mock import MagicMock, patch

import panel as pn
import pytest

from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession


class TestGuiEdgeCases:
    """
    Test edge cases for the GUI: empty database, missing nodes, etc.
    """

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        engine = MagicMock(spec=InteractiveRaptorEngine)
        engine.get_root_node.return_value = None
        engine.get_node.return_value = None
        engine.get_children.return_value = []
        return engine

    @pytest.fixture
    def session(self, mock_engine: MagicMock) -> InteractiveSession:
        return InteractiveSession(engine=mock_engine)

    @pytest.fixture
    def canvas(self, session: InteractiveSession) -> MatomeCanvas:
        return MatomeCanvas(session)

    def test_empty_database_view(self, canvas: MatomeCanvas, session: InteractiveSession) -> None:
        """
        Verify that an empty database (no root node) renders a safe default view.
        """
        session.load_tree()

        # Call internal method directly
        details_col = canvas._render_node_details(None, False)
        # Type assertion for MyPy
        assert isinstance(details_col, pn.Column)
        # Casting to Any or dynamic access for test simplicity
        # Use simple object access which is valid for Markdown pane but mypy doesn't know details_col[0] is Markdown
        # We can use typing.cast or just ignore since we asserted isinstance above?
        # MyPy sees Viewable which doesn't have object. We need to cast.
        from panel.pane import Markdown
        assert isinstance(details_col[0], Markdown)
        assert "Select a node" in details_col[0].object

        # Use internal method for pyramid view
        pyramid_view = canvas._render_pyramid_nodes([])
        assert isinstance(pyramid_view, Markdown)
        assert "No child nodes" in pyramid_view.object

    def test_missing_node_selection(self, canvas: MatomeCanvas, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """
        Verify that selecting a non-existent node (e.g. deleted or bad ID) is handled.
        """
        mock_engine.get_node.return_value = None
        session.select_node("missing_id")
        assert session.selected_node is None

        details_col = canvas._render_node_details(None, False)
        assert isinstance(details_col, pn.Column)
        from panel.pane import Markdown
        assert isinstance(details_col[0], Markdown)
        assert "Select a node" in details_col[0].object

    def test_broken_node_rendering(self, canvas: MatomeCanvas, session: InteractiveSession) -> None:
        """
        Verify that if rendering fails (e.g. Panel internal error), UI catches exception.
        """
        valid_node = SummaryNode(
            id="node_1",
            text="Text",
            level=2,
            children_indices=[],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )

        with patch("matome.ui.canvas.pn.widgets.TextAreaInput", side_effect=ValueError("Widget Boom")):
             details_col = canvas._render_node_details(valid_node, False)

             assert isinstance(details_col, pn.Column)
             from panel.pane import Markdown
             assert isinstance(details_col[0], Markdown)
             assert "Error rendering details: Widget Boom" in details_col[0].object
