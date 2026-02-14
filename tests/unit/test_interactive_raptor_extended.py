from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.utils.store import DiskChunkStore


class TestInteractiveRaptorEngineExtended:
    @pytest.fixture
    def mock_store(self) -> MagicMock:
        return MagicMock(spec=DiskChunkStore)

    @pytest.fixture
    def config(self) -> ProcessingConfig:
        return ProcessingConfig()

    def test_init_optional_summarizer(self, mock_store: MagicMock, config: ProcessingConfig) -> None:
        """Test initializing without a summarizer (read-only mode)."""
        engine = InteractiveRaptorEngine(store=mock_store, summarizer=None, config=config)
        assert engine.store == mock_store
        assert engine.summarizer is None
        assert engine.config == config

    def test_get_root_node_found(self, mock_store: MagicMock, config: ProcessingConfig) -> None:
        """Test retrieving the root node when it exists."""
        engine = InteractiveRaptorEngine(store=mock_store, summarizer=None, config=config)

        # Mock store.get_node_ids_by_level to return nodes at level 3, then nothing at 4
        # Wait, how will get_root_node work?
        # Strategy: Search downwards from MAX_LEVEL (e.g. 10) until nodes are found.
        # Suppose root is at level 3.

        from collections.abc import Iterator
        def side_effect(level: int) -> Iterator[str]:
            if level == 3:
                yield "root_id"
            else:
                # To satisfy return type Iterator[str], we yield from nothing
                yield from []

        mock_store.get_max_level.return_value = 3
        mock_store.get_node_ids_by_level.side_effect = side_effect

        root_node = SummaryNode(
            id="root_id",
            text="Root Text",
            level=3,
            children_indices=[],
            metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
        )
        mock_store.get_node.return_value = root_node

        # We assume get_root_node searches from some high level down to 1
        found_node = engine.get_root_node()

        assert found_node == root_node
        mock_store.get_node.assert_called_with("root_id")

    def test_get_root_node_not_found(self, mock_store: MagicMock, config: ProcessingConfig) -> None:
        """Test retrieving root node when tree is empty."""
        engine = InteractiveRaptorEngine(store=mock_store, summarizer=None, config=config)

        # All levels empty
        mock_store.get_node_ids_by_level.return_value = iter([])

        found_node = engine.get_root_node()
        assert found_node is None

    def test_refine_node_fails_without_summarizer(self, mock_store: MagicMock, config: ProcessingConfig) -> None:
        """Test that refine_node raises error if summarizer is missing."""
        engine = InteractiveRaptorEngine(store=mock_store, summarizer=None, config=config)

        with pytest.raises(RuntimeError, match="Summarizer agent is not initialized"):
            engine.refine_node("some_id", "Make it better")
