from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from matome.cli import app


class TestCLIMemorySafety:
    @pytest.fixture
    def mock_store(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_raptor(self) -> MagicMock:
        return MagicMock()

    def test_streaming_input(self, tmp_path: Path, mock_store: MagicMock, mock_raptor: MagicMock) -> None:
        """Verify that input is passed as a generator (streaming)."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("Line 1\nLine 2\nLine 3")

        runner = CliRunner()

        # Mock dependencies inside the test to ensure they are used
        with patch("matome.cli.RaptorEngine") as MockRaptor, \
             patch("matome.cli.DiskChunkStore"), \
             patch("matome.cli._stream_file_content") as mock_stream:

            # Setup mocks
            mock_instance = MockRaptor.return_value
            mock_raptor.return_value = mock_instance # Align with fixture logic if needed, but patch handles it

            # We mock stream to return a known generator object
            mock_gen = iter(["chunk1", "chunk2"])
            mock_stream.return_value = mock_gen

            result = runner.invoke(app, ["run", str(input_file), "--no-verify"])

            assert result.exit_code == 0

            assert mock_instance.run.called
            args, _ = mock_instance.run.call_args
            text_arg = args[0]

            # Verify the generator passed to run() matches what we returned from stream
            assert text_arg is mock_gen
            assert list(text_arg) == ["chunk1", "chunk2"]
