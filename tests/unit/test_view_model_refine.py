from typing import Any
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.ui.view_model import InteractiveSession
from matome.utils.store import DiskChunkStore


class TestInteractiveSessionRefine:

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        return MagicMock(spec=DiskChunkStore)

    @pytest.fixture
    def mock_engine(self, mock_store: MagicMock) -> MagicMock:
        config = ProcessingConfig()
        engine = InteractiveRaptorEngine(store=mock_store, summarizer=None, config=config)
        engine.refine_node = MagicMock()  # type: ignore[method-assign]
        return engine  # type: ignore[return-value]

    @pytest.fixture
    def session(self, mock_engine: MagicMock) -> InteractiveSession:
        return InteractiveSession(engine=mock_engine)

    def test_refine_success(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test successful refinement updates selected_node and handles is_processing."""
        # Setup initial node
        original_node = SummaryNode(
            id="node_1",
            text="Original",
            level=2,
            children_indices=[1, 2],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )
        session.selected_node = original_node

        # Setup engine response
        refined_node = SummaryNode(
            id="node_1",
            text="Refined",
            level=2,
            children_indices=[1, 2],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE, is_user_edited=True)
        )
        mock_engine.refine_node.return_value = refined_node

        # Track is_processing state changes
        states = []
        def observer(event: Any) -> None:
            states.append(event.new)

        session.param.watch(observer, ['is_processing'])

        # Set breadcrumbs including the node to be refined
        session.breadcrumbs = [original_node]

        # Execute
        instruction = "Make it better"
        session.refine_current_node(instruction)

        # Verify
        mock_engine.refine_node.assert_called_once_with("node_1", instruction)
        assert session.selected_node == refined_node
        assert session.selected_node.text == "Refined"

        # Verify breadcrumbs updated
        assert len(session.breadcrumbs) == 1
        assert session.breadcrumbs[0] == refined_node
        assert session.breadcrumbs[0].text == "Refined"

        # Verify is_processing toggled True then False
        # Note: param watcher might catch initial True set, then False set
        # Since default is False, first change is True, then False.
        assert True in states
        assert states[-1] is False
        assert session.is_processing is False

    def test_refine_no_selection(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test refinement does nothing if no node selected."""
        session.selected_node = None
        session.refine_current_node("instruction")

        mock_engine.refine_node.assert_not_called()
        assert session.is_processing is False

    def test_refine_error_handling(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test is_processing resets even if engine raises error."""
        session.selected_node = SummaryNode(
            id="node_1",
            text="Original",
            level=2,
            children_indices=[],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )

        mock_engine.refine_node.side_effect = ValueError("Engine Error")

        with pytest.raises(ValueError, match="Engine Error"):
            session.refine_current_node("instruction")

        assert session.is_processing is False

    def test_refine_chunk_error(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test attempting to refine a chunk raises error or handled by engine."""
        # Engine raises TypeError for chunks
        chunk = Chunk(index=1, text="Chunk", start_char_idx=0, end_char_idx=10)
        session.selected_node = chunk

        # Mock engine behavior for chunk
        # Actually refine_node takes ID, so if we pass ID, engine handles type check
        mock_engine.refine_node.side_effect = TypeError("Only SummaryNodes can be refined")

        with pytest.raises(TypeError):
            session.refine_current_node("instruction")

        assert session.is_processing is False
