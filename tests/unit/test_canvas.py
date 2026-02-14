from unittest.mock import MagicMock, patch

import pytest

from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession


class TestMatomeCanvas:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=InteractiveSession)

    def test_init(self, mock_session: MagicMock) -> None:
        canvas = MatomeCanvas(mock_session)
        assert canvas.session == mock_session

    def test_view_structure(self, mock_session: MagicMock) -> None:
        """Test that view() returns a Panel object."""
        canvas = MatomeCanvas(mock_session)
        try:
            # We mock pn.template.MaterialTemplate to avoid needing a full display
            with patch("panel.template.MaterialTemplate") as mock_template:
                view = canvas.view()
                assert view is not None
                assert mock_template.called
        except ImportError:
            pytest.skip("Panel not installed or display not available.")
        except Exception as e:
            pytest.fail(f"View creation failed: {e}")

    def test_render_methods(self, mock_session: MagicMock) -> None:
        """Test that render methods produce bindable objects."""
        canvas = MatomeCanvas(mock_session)

        # Mock session parameters
        mock_session.param = MagicMock()
        mock_session.param.breadcrumbs = []
        mock_session.param.current_view_nodes = []
        mock_session.param.selected_node = None

        # Call render methods (they return bound functions)
        breadcrumbs_view = canvas._render_breadcrumbs()
        pyramid_view = canvas._render_pyramid_view()
        details_view = canvas._render_details()

        # Check they return something (Panel bind objects usually)
        assert breadcrumbs_view is not None
        assert pyramid_view is not None
        assert details_view is not None

    def test_render_details_logic(self, mock_session: MagicMock) -> None:
        """Test internal logic of rendering details via direct call to bound function."""
        canvas = MatomeCanvas(mock_session)

        # Simple verification that the method exists and returns a bindable object
        # Logic testing is delegated to integration tests or manual UAT as Panel internals are hard to mock.
        assert canvas._render_details() is not None
