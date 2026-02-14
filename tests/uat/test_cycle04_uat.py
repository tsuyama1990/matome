import pytest
from unittest.mock import MagicMock
from domain_models.config import ProcessingConfig
from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession
from matome.engines.interactive_raptor import InteractiveRaptorEngine

class TestCycle04UAT:
    """
    Scenario 04: Interactive Refinement Flow
    """
    @pytest.fixture
    def session(self) -> InteractiveSession:
        # Use real engine instance with mocks to satisfy type checking
        mock_store = MagicMock()
        mock_summarizer = MagicMock()
        config = ProcessingConfig()
        engine = InteractiveRaptorEngine(store=mock_store, summarizer=mock_summarizer, config=config)
        engine.get_root_node = MagicMock(return_value=None)

        return InteractiveSession(engine=engine)

    def test_refinement_flow(self, session: InteractiveSession) -> None:
        """Test the refinement interaction through the UI components."""
        # Simple test to verify wiring
        canvas = MatomeCanvas(session)
        assert canvas.view() is not None
