import pytest
from unittest.mock import MagicMock, patch
import panel as pn
from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from domain_models.manifest import SummaryNode, NodeMetadata, Chunk
from domain_models.types import DIKWLevel, NodeID
from domain_models.config import ProcessingConfig

class TestGuiEdgeCases:
    @pytest.fixture
    def session(self) -> InteractiveSession:
        # Create a mock that is an instance of InteractiveRaptorEngine to satisfy param validation
        # We can't just use MagicMock(spec=...) because param checks isinstance
        # But we can try to mock the class or just instantiate it with mocks.
        # Instantiating with mocks is safer.

        mock_store = MagicMock()
        mock_summarizer = MagicMock()
        config = ProcessingConfig()

        engine = InteractiveRaptorEngine(store=mock_store, summarizer=mock_summarizer, config=config)
        # Mock methods we need
        engine.get_root_node = MagicMock(return_value=None)
        engine.get_node = MagicMock(return_value=None)
        engine.get_children = MagicMock(return_value=iter([]))

        session = InteractiveSession(engine=engine)
        return session

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
        assert "Select a node" in details[0].object

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
             # In new canvas, we log exception but still return a markdown with generic error or specific message
             # The code says: return pn.Column(pn.pane.Markdown("Error rendering details", styles={"color": "red"}))
             assert "Error rendering details" in details_col[0].object
