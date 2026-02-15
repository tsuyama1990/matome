from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.exceptions import MatomeError


class TestInteractiveRaptorEngineExtended:
    @pytest.fixture
    def mock_store(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def config(self) -> ProcessingConfig:
        return ProcessingConfig()

    def test_get_root_node_not_found(self, mock_store: MagicMock, config: ProcessingConfig) -> None:
        """Test retrieving root node when tree is empty."""
        engine = InteractiveRaptorEngine(store=mock_store, summarizer=None, config=config)

        # All levels empty
        mock_store.get_max_level.return_value = 1
        mock_store.get_node_ids_by_level.return_value = iter([])

        with pytest.raises(MatomeError, match="Max level is 1 but no nodes found"):
            engine.get_root_node()

    def test_single_node_refinement_cycle(self, mock_store: MagicMock, config: ProcessingConfig) -> None:
        """Test full refinement cycle including updates."""
        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = "Refined"

        engine = InteractiveRaptorEngine(store=mock_store, summarizer=mock_summarizer, config=config)

        node = SummaryNode(
            id="n1", text="Orig", level=1, children_indices=[0],
            metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
        )
        mock_store.get_node.return_value = node
        # Mock children fetching (needs one child)
        mock_store.get_nodes.return_value = iter([MagicMock(text="Child", index=0)])

        res = engine.refine_node("n1", "Make better")

        assert res.text == "Refined"
        assert res.metadata.is_user_edited
        mock_store.update_node.assert_called_once()
