import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from domain_models.config import ProcessingConfig
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.exceptions import RefinementError, StoreError
from matome.utils.store import DiskChunkStore


def test_store_connection_failure() -> None:
    """Test that StoreError is raised on DB connection failure."""
    with patch("matome.utils.store.create_engine") as mock_create:
        mock_create.side_effect = SQLAlchemyError("Connection refused")
        with pytest.raises(StoreError, match="Failed to create database engine"):
            DiskChunkStore()


def test_store_query_failure(tmp_path: Path) -> None:
    """Test handling of query failures."""
    store = DiskChunkStore(db_path=tmp_path / "test.db")

    # Simulate DB error during get_node
    with patch.object(store.engine, "connect") as mock_connect:
        mock_connect.side_effect = SQLAlchemyError("DB Lock")
        with pytest.raises(StoreError, match="Failed to retrieve node"):
            store.get_node("123")

    store.close()


def test_corrupted_json_in_db(tmp_path: Path) -> None:
    """Test handling of corrupted JSON data in the database."""
    store = DiskChunkStore(db_path=tmp_path / "corrupt.db")

    # We expect an OperationalError from SQLite when inserting bad JSON into an indexed JSON column
    # or a ValueError/StoreError if we manage to get it in and then read it.
    # Here we test that the store rejects or the DB rejects invalid JSON insertion if checks are in place.
    try:
        with store.engine.begin() as conn:
            from sqlalchemy import insert
            conn.execute(
                insert(store.nodes_table).values(
                    id="bad_node",
                    type="chunk",
                    content="{invalid json",
                    embedding=None
                )
            )
    except SQLAlchemyError:
        # Expected behavior if DB constraints/indexes prevent insertion
        pass
    else:
        # If insertion succeeded, reading it should fail
        with pytest.raises(ValueError, match="Failed to decode JSON"):
            store.get_node("bad_node")

    store.close()


def test_refinement_store_failure(tmp_path: Path) -> None:
    """Test that InteractiveRaptorEngine wraps store errors."""
    store = MagicMock(spec=DiskChunkStore)
    store.get_node.side_effect = StoreError("DB unavailable")

    config = ProcessingConfig(max_instruction_length=1000)

    engine = InteractiveRaptorEngine(store=store, summarizer=MagicMock(), config=config)

    with pytest.raises(RefinementError, match="Refinement failed"):
        engine.refine_node("node_1", "make it better")


def test_empty_database(tmp_path: Path) -> None:
    """Test operations on an empty database."""
    store = DiskChunkStore(db_path=tmp_path / "empty.db")

    assert store.get_node("non_existent") is None
    assert list(store.get_nodes(["missing1", "missing2"])) == []
    assert store.get_node_count(0) == 0
    assert store.get_max_level() == 0

    store.close()
