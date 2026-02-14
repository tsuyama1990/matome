from unittest.mock import MagicMock
import pytest
import panel as pn
from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession

class TestMatomeCanvas:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        session = MagicMock(spec=InteractiveSession)
        session.param = MagicMock()
        session.param.breadcrumbs = []
        session.param.current_view_nodes = []
        session.param.selected_node = None
        session.param.is_processing = False
        return session

    def test_view_structure(self, mock_session: MagicMock) -> None:
        """Test that view() constructs the template correctly calling render methods."""
        canvas = MatomeCanvas(mock_session)

        # Call view to trigger rendering
        template = canvas.view()

        assert isinstance(template, pn.template.MaterialTemplate)
        assert template.title == "Matome: Knowledge Installation"
        assert len(template.main) == 1
        assert len(template.sidebar) == 1

        # Verify main area is a Column
        main_area = template.main[0]
        assert isinstance(main_area, pn.Column)

        # It should contain breadcrumbs and pyramid view (as bind objects or Rows/FlexBox)
        # Since we use pn.bind, the objects in the Column might be functions or Viewables.
        assert len(main_area.objects) >= 2

    def test_render_methods_return_viewables(self, mock_session: MagicMock) -> None:
        """Test that individual render methods return Viewable objects or Binders."""
        canvas = MatomeCanvas(mock_session)

        breadcrumbs = canvas._render_breadcrumbs()
        assert breadcrumbs is not None

        pyramid = canvas._render_pyramid_view()
        assert pyramid is not None

        details = canvas._render_details()
        assert details is not None
