from unittest.mock import MagicMock

import pytest
from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession


class TestMatomeCanvas:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=InteractiveSession)

    def test_init(self, mock_session):
        canvas = MatomeCanvas(mock_session)
        assert canvas.session == mock_session

    def test_view_structure(self, mock_session):
        """Test that view() returns a Panel object (mocked or real)."""
        # This test might be fragile if Panel requires a display server.
        # We'll just check if the method exists and runs without error.
        canvas = MatomeCanvas(mock_session)
        try:
            view = canvas.view()
            assert view is not None
        except ImportError:
            pytest.skip("Panel not installed or display not available.")
        except Exception as e:
            pytest.fail(f"View creation failed: {e}")
