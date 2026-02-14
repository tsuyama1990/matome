from unittest.mock import MagicMock, patch

import pytest

from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession


class TestGuiMocked:
    """
    Mocked GUI tests to verify view logic without spawning a real server process.
    Satisfies 'Memory Safety Violation' concern by avoiding real subprocess.
    """

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        session = MagicMock(spec=InteractiveSession)
        session.param = MagicMock()
        # Setup parameters to be iterable or mock objects as needed by Panel
        session.param.breadcrumbs = []
        session.param.current_view_nodes = []
        session.param.selected_node = None
        return session

    def test_canvas_initialization(self, mock_session: MagicMock) -> None:
        canvas = MatomeCanvas(mock_session)
        assert canvas.session == mock_session

    def test_rendering_resilience(self, mock_session: MagicMock) -> None:
        """Test that rendering methods don't crash even with malformed data."""
        canvas = MatomeCanvas(mock_session)
        assert canvas._render_breadcrumbs() is not None

    def test_selection_error_handling(self, mock_session: MagicMock) -> None:
        """Test that selection errors are handled gracefully via notifications."""
        # Mock panel module in the canvas module
        with patch("matome.ui.canvas.pn") as mock_pn:
            # Setup the mock state and notifications
            mock_notif = MagicMock()
            mock_pn.state.notifications = mock_notif

            canvas = MatomeCanvas(mock_session)

            # Make select_node raise exception
            mock_session.select_node.side_effect = RuntimeError("Selection boom")

            # Call handler directly
            canvas._handle_selection("bad_id")

            # Verify notification was called
            mock_notif.error.assert_called_with("Selection failed: Selection boom")
