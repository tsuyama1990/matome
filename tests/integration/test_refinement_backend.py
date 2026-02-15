import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.agents.summarizer import SummarizationAgent
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.exceptions import RefinementError
from matome.utils.store import DiskChunkStore


class TestInteractiveRefinementBackend:
    """
    Integration test for InteractiveRaptorEngine.refine_node.
    Uses a real DiskChunkStore (SQLite) but mocks the SummarizationAgent (LLM).
    """

    @pytest.fixture
    def temp_store(self) -> Generator[DiskChunkStore, None, None]:
        """Create a temporary DiskChunkStore."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_chunks.db"
            store = DiskChunkStore(db_path=db_path)
            yield store
            store.close()

    @pytest.fixture
    def mock_summarizer(self) -> MagicMock:
        """Mock the SummarizationAgent."""
        summarizer = MagicMock(spec=SummarizationAgent)
        summarizer.summarize.return_value = "Refined Summary Content"
        return summarizer

    @pytest.fixture
    def engine(self, temp_store: DiskChunkStore, mock_summarizer: MagicMock) -> InteractiveRaptorEngine:
        """Create the engine with mocked summarizer."""
        config = ProcessingConfig()
        return InteractiveRaptorEngine(store=temp_store, summarizer=mock_summarizer, config=config)

    def test_refine_node_integration(
        self, engine: InteractiveRaptorEngine, temp_store: DiskChunkStore, mock_summarizer: MagicMock
    ) -> None:
        """
        Verify that refine_node retrieves children, calls summarizer, and updates store.
        """
        # 1. Setup Data in Store
        chunk1 = Chunk(index=1, text="Child 1", start_char_idx=0, end_char_idx=10)
        chunk2 = Chunk(index=2, text="Child 2", start_char_idx=11, end_char_idx=20)

        parent_node = SummaryNode(
            id="node_1",
            text="Original Summary",
            level=2,
            children_indices=[1, 2],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )

        with temp_store as store:
            store.add_chunk(chunk1)
            store.add_chunk(chunk2)
            store.add_summary(parent_node)

            # 2. Execute Refinement
            instruction = "Simplify this."
            updated_node = engine.refine_node("node_1", instruction)

            # 3. Verify Result
            assert updated_node.text == "Refined Summary Content"
            assert updated_node.metadata.is_user_edited is True
            assert updated_node.metadata.refinement_history == ["Simplify this."]

            # Verify Persistence
            persisted = store.get_node("node_1")
            assert isinstance(persisted, SummaryNode)
            assert persisted.text == "Refined Summary Content"
            assert persisted.metadata.is_user_edited is True

    def test_refine_node_error_handling(
        self, engine: InteractiveRaptorEngine, temp_store: DiskChunkStore, mock_summarizer: MagicMock
    ) -> None:
        """
        Verify error handling when summarizer fails or DB issues occur.
        """
        parent_node = SummaryNode(
            id="node_fail",
            text="Original",
            level=2,
            children_indices=[],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )

        # We need children to refine
        chunk = Chunk(index=1, text="Child", start_char_idx=0, end_char_idx=5)

        with temp_store as store:
            store.add_summary(parent_node)
            # Add child BUT we will fail retrieval or summarization
            store.add_chunk(chunk)

            # Update parent to point to child
            # (Note: SummaryNode is immutable in Pydantic so we create new one or update in DB directly?
            # Actually we can just re-add it, store handles overwrite if ID same)
            parent_node = parent_node.model_copy(update={"children_indices": [1]})
            store.add_summary(parent_node)

            # Case 1: Summarizer Failure
            mock_summarizer.summarize.side_effect = RuntimeError("LLM Down")

            with pytest.raises(RefinementError, match="LLM Down"):
                engine.refine_node("node_fail", "instr")

            # Verify node NOT updated
            node = store.get_node("node_fail")
            assert isinstance(node, SummaryNode)
            assert node.text == "Original"
            assert not node.metadata.is_user_edited

            # Case 2: Invalid Node ID
            with pytest.raises(RefinementError, match="Node .* not found"):
                engine.refine_node("invalid_id", "instr")
