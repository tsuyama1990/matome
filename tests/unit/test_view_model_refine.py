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
        original_node = SummaryNode(
            id="node_1",
            text="Original",
            level=2,
            children_indices=[1, 2],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )
        session.selected_node = original_node

        refined_node = SummaryNode(
            id="node_1",
            text="Refined",
            level=2,
            children_indices=[1, 2],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE, is_user_edited=True)
        )
        mock_engine.refine_node.return_value = refined_node

        session.breadcrumbs = [original_node]
        session.refine_current_node("Make it better")

        mock_engine.refine_node.assert_called_once_with("node_1", "Make it better")
        assert session.selected_node == refined_node
        assert session.breadcrumbs[0] == refined_node
        assert session.is_processing is False

    def test_multiple_refinements(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test that state remains consistent after multiple refinements."""
        # Initial State
        node_v1 = SummaryNode(
            id="node_1",
            text="V1",
            level=2,
            children_indices=[1],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )
        session.selected_node = node_v1
        session.breadcrumbs = [node_v1]

        # Refinement 1
        node_v2 = node_v1.model_copy(update={"text": "V2"})
        node_v2.metadata.is_user_edited = True
        mock_engine.refine_node.return_value = node_v2

        session.refine_current_node("Refine 1")

        assert session.selected_node.text == "V2"
        assert session.breadcrumbs[0].text == "V2"

        # Refinement 2
        node_v3 = node_v2.model_copy(update={"text": "V3"})
        mock_engine.refine_node.return_value = node_v3

        session.refine_current_node("Refine 2")

        assert session.selected_node.text == "V3"
        assert session.breadcrumbs[0].text == "V3"
        assert len(session.breadcrumbs) == 1

    def test_refine_no_selection(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        session.selected_node = None
        session.refine_current_node("instruction")
        mock_engine.refine_node.assert_not_called()

    def test_refine_error_handling(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
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
        chunk = Chunk(index=1, text="Chunk", start_char_idx=0, end_char_idx=10)
        session.selected_node = chunk

        # Engine raises TypeError if ID passed points to chunk, but View Model should block first?
        # Our view model check: if not isinstance(self.selected_node, SummaryNode): raise TypeError

        with pytest.raises(TypeError):
            session.refine_current_node("instruction")
