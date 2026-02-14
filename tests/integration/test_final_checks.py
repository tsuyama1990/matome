import pytest
from unittest.mock import MagicMock
from pathlib import Path
from sqlalchemy import text

from matome.utils.store import DiskChunkStore
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from domain_models.config import ProcessingConfig
from domain_models.manifest import SummaryNode, NodeMetadata, Chunk
from domain_models.types import DIKWLevel

def test_wal_mode(tmp_path: Path) -> None:
    """Verify WAL mode is enabled in DiskChunkStore."""
    db_path = tmp_path / "test_wal.db"
    store = DiskChunkStore(db_path=db_path)

    try:
        with store.engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode;"))
            mode = result.scalar()
            assert mode == "wal", f"Expected WAL mode, got {mode}"
    finally:
        store.close()

def test_refine_node_metadata_updated(tmp_path: Path) -> None:
    """Verify metadata integrity after refinement."""
    store = DiskChunkStore(db_path=tmp_path / "test_meta.db")

    # Setup Data
    node_id = "test_node_1"
    child = Chunk(index=0, text="Child content", start_char_idx=0, end_char_idx=10)
    node = SummaryNode(
        id=node_id,
        text="Original Text",
        level=1,
        children_indices=[0],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )

    store.add_chunk(child)
    store.add_summary(node)

    # Mock Summarizer
    mock_summarizer = MagicMock()
    mock_summarizer.summarize.return_value = "Refined Text"

    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(store=store, summarizer=mock_summarizer, config=config)

    # Action
    instruction = "Improve clarity"
    engine.refine_node(node_id, instruction)

    # Verification
    updated_node = store.get_node(node_id)
    assert isinstance(updated_node, SummaryNode)
    assert updated_node.text == "Refined Text"
    assert updated_node.metadata.is_user_edited is True
    assert instruction in updated_node.metadata.refinement_history

    store.close()
