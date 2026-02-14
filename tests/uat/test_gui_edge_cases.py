from unittest.mock import MagicMock, patch

import panel as pn
import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession


class TestGuiEdgeCases:
    @pytest.fixture
    def session(self) -> InteractiveSession:
        # Create a mock engine that satisfies the type checker
        mock_store = MagicMock()
        mock_summarizer = MagicMock()
        config = ProcessingConfig()

        # We use a real instance but we will patch its methods
        engine = InteractiveRaptorEngine(store=mock_store, summarizer=mock_summarizer, config=config)

        # Use patch.object to mock methods on the instance without assigning directly
        # which causes mypy error "Cannot assign to a method"
        with patch.object(engine, 'get_root_node', return_value=None), \
             patch.object(engine, 'get_node', return_value=None), \
             patch.object(engine, 'get_children', return_value=iter([])):
            return InteractiveSession(engine=engine)

    @pytest.fixture
    def canvas(self, session: InteractiveSession) -> MatomeCanvas:
        return MatomeCanvas(session)

    def test_empty_database_view(self, canvas: MatomeCanvas, session: InteractiveSession) -> None:
        """Verify UI handles empty state gracefully."""
        # Set state to empty
        session.root_node = None
        session.breadcrumbs = []
        session.current_view_nodes = []

        # Render main area
        col = canvas._render_main_area()
        assert isinstance(col, pn.Column)

        # Render pyramid view directly to check empty state message
        view = canvas._render_pyramid_nodes([])
        assert isinstance(view, pn.pane.Markdown)
        assert "No child nodes" in view.object

    def test_missing_node_selection(self, canvas: MatomeCanvas, session: InteractiveSession) -> None:
        """Verify details panel handles None selection."""
        session.selected_node = None

        details = canvas._render_node_details(None, False)
        assert isinstance(details, pn.Column)
        # Type narrowing for mypy
        first_item = details[0]
        assert hasattr(first_item, "object")
        assert "Select a node" in first_item.object

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
             # Check error message
             error_pane = details_col[0]
             assert hasattr(error_pane, "object")
             assert "Error rendering details" in error_pane.object
