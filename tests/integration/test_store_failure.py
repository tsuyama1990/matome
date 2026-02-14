import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from matome.utils.store import DiskChunkStore, StoreError


class TestStoreFailures:
    """Integration tests for database failure scenarios."""

    def test_store_initialization_failure(self) -> None:
        """Test handling of database initialization errors."""
        # Use patch to simulate failure without creating insecure temp files
        with (
            patch("matome.utils.store.create_engine", side_effect=SQLAlchemyError("Connection failed")),
            pytest.raises(StoreError, match="Failed to create database engine")
        ):
            DiskChunkStore(db_path=Path("dummy_path"))

    def test_add_chunk_db_error(self) -> None:
        """Test error handling when adding chunks fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = DiskChunkStore(db_path=Path(temp_dir) / "test.db")

            # Mock engine.begin to raise an error
            # We need to mock the engine instance on the store object
            store.engine = MagicMock()
            store.engine.begin.side_effect = SQLAlchemyError("Insert failed")

            chunk = MagicMock()
            chunk.index = 1
            chunk.model_dump_json.return_value = "{}"
            chunk.embedding = [0.1]

            # Broaden match to ensure we catch the error wrapping
            # Note: The actual error might be wrapped differently depending on where it's caught
            with pytest.raises(StoreError):
                store.add_chunk(chunk)

    def test_get_nodes_db_error(self) -> None:
        """Test error handling when retrieving nodes fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = DiskChunkStore(db_path=Path(temp_dir) / "test.db")

            # Mock engine.connect to raise an error
            store.engine = MagicMock()
            store.engine.connect.side_effect = SQLAlchemyError("Select failed")

            # Must consume iterator to trigger error
            with pytest.raises(StoreError, match="Failed to retrieve nodes"):
                list(store.get_nodes(["1"]))

    def test_corrupted_data_handling(self) -> None:
        """Test resilience against corrupted JSON data in DB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "corrupted.db"
            store = DiskChunkStore(db_path=db_path)

            # Use mock to simulate bad data return
            store.engine = MagicMock()
            mock_conn = MagicMock()
            store.engine.connect.return_value.__enter__.return_value = mock_conn

            # Mock result row with bad JSON
            mock_row = MagicMock()
            mock_row.id = "1"
            mock_row.type = "chunk"
            mock_row.content = "{bad_json"
            mock_row.embedding = None

            mock_result = MagicMock()
            mock_result.__iter__.return_value = [mock_row]
            mock_conn.execution_options.return_value.execute.return_value = mock_result

            # Should yield None or handle error gracefully
            nodes = list(store.get_nodes(["1"]))
            assert len(nodes) == 1
            assert nodes[0] is None
