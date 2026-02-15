from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.ui.view_model import InteractiveSession
from matome.utils.store import DiskChunkStore


class TestInteractiveSession:

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        return MagicMock(spec=DiskChunkStore)

    @pytest.fixture
    def mock_engine(self, mock_store: MagicMock) -> MagicMock:
        config = ProcessingConfig()
        # Use a real instance with mock store, mocking methods as needed
        engine = InteractiveRaptorEngine(store=mock_store, summarizer=None, config=config)
        engine.get_root_node = MagicMock()  # type: ignore[method-assign]
        engine.get_node = MagicMock()  # type: ignore[method-assign]
        engine.get_children = MagicMock()  # type: ignore[method-assign]
        return engine  # type: ignore[return-value]

    @pytest.fixture
    def session(self, mock_engine: MagicMock) -> InteractiveSession:
        return InteractiveSession(engine=mock_engine)

    def test_init(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        assert session.engine == mock_engine
        assert session.selected_node is None
        assert session.breadcrumbs == []
        assert session.current_view_nodes == []

    def test_load_tree_success(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test loading the tree successfully sets the root node."""
        root = SummaryNode(
            id="root_123",
            text="Root Text",
            level=3,
            children_indices=[1, 2],
            metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
        )
        mock_engine.get_root_node.return_value = root
        mock_engine.get_node.return_value = root
        mock_engine.get_children.return_value = []

        session.load_tree()

        assert session.root_node == root
        assert session.selected_node == root
        assert session.breadcrumbs == [root]
        mock_engine.get_root_node.assert_called_once()

    def test_load_tree_empty(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test behavior when no tree is found."""
        mock_engine.get_root_node.return_value = None
        session.load_tree()
        assert session.root_node is None

    def test_select_node_summary(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test selecting a summary node."""
        parent = SummaryNode(
            id="root_123",
            text="Parent",
            level=2,
            children_indices=["child_1"],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )
        child = SummaryNode(
            id="child_1",
            text="Child",
            level=1,
            children_indices=[100],
            metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
        )
        grandchild = Chunk(
            index=100,
            text="Raw Data",
            start_char_idx=0,
            end_char_idx=10,
        )

        # Setup initial state
        session.root_node = parent
        session.breadcrumbs = [parent]

        # Setup engine returns
        mock_engine.get_node.side_effect = lambda nid: {"root_123": parent, "child_1": child, "100": grandchild}.get(str(nid))
        mock_engine.get_children.return_value = [grandchild]

        # Action: Select child
        session.select_node("child_1")

        assert session.selected_node == child
        assert session.breadcrumbs == [parent, child]
        assert session.current_view_nodes == [grandchild]

    def test_select_node_chunk(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test selecting a chunk node (leaf)."""
        # ... setup similar to above but selecting a chunk ...
        # For brevity, let's assume selecting a chunk works similarly
        chunk = Chunk(index=99, text="Data", start_char_idx=0, end_char_idx=10)
        mock_engine.get_node.return_value = chunk
        mock_engine.get_children.return_value = [] # Chunks have no children

        session.select_node("99")

        assert session.selected_node == chunk
        assert session.current_view_nodes == []

    def test_navigate_up(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test selecting a node already in breadcrumbs (navigating up)."""
        root = SummaryNode(id="root", text="R", level=3, children_indices=[], metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM))
        child = SummaryNode(id="child", text="C", level=2, children_indices=[], metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE))

        session.root_node = root
        session.breadcrumbs = [root, child]
        session.selected_node = child

        mock_engine.get_node.return_value = root
        mock_engine.get_children.return_value = [child]

        session.select_node("root")

        assert session.selected_node == root
        assert session.breadcrumbs == [root] # Should truncate path
        assert session.current_view_nodes == [child]

    def test_load_source_chunks(self, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """Test loading source chunks."""
        c1 = Chunk(index=1, text="C1", start_char_idx=0, end_char_idx=2)
        c2 = Chunk(index=2, text="C2", start_char_idx=3, end_char_idx=5)

        # Mock the method explicitly as mock_engine is a real instance
        mock_engine.get_source_chunks = MagicMock(return_value=[c1, c2])

        session.load_source_chunks("node_1")

        mock_engine.get_source_chunks.assert_called_once_with("node_1")
        assert session.source_chunks == [c1, c2]
        assert session.show_source_chunks is True
