from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from matome.cli import app
from matome.utils.store import DiskChunkStore


class TestCLIMemorySafety:
    """
    Tests for CLI memory safety features (streaming, file size limits).
    """

    @pytest.fixture
    def mock_store(self) -> Generator[MagicMock, None, None]:
        with patch("matome.cli.DiskChunkStore") as mock:
            # Setup context manager mock
            mock_instance = mock.return_value
            mock_instance.__enter__.return_value = mock_instance
            yield mock

    @pytest.fixture
    def mock_raptor(self) -> Generator[MagicMock, None, None]:
        with patch("matome.cli.RaptorEngine") as mock:
            yield mock

    def test_file_size_limit_enforcement(self, tmp_path) -> None:
        """Verify CLI rejects files exceeding the size limit."""
        # Create a large dummy file
        large_file = tmp_path / "large.txt"
        large_file.write_text("A" * 2000) # 2KB

        # Mock config to have a small limit
        # We need to patch ProcessingConfig default or pass args if possible.
        # Since CLI uses defaults, we can mock ProcessingConfig.default()

        from domain_models.config import ProcessingConfig

        # Create a config with small limit
        small_config = ProcessingConfig(max_file_size_bytes=1024) # 1KB

        with patch("matome.cli.ProcessingConfig") as MockConfig:
            # Mock constructor to return our small config
            MockConfig.return_value = small_config

            # Since typer catches exceptions, we invoke via runner
            from typer.testing import CliRunner
            runner = CliRunner()

            result = runner.invoke(app, ["run", str(large_file)])

            assert result.exit_code != 0
            assert "File too large" in result.stderr

    def test_streaming_input(self, tmp_path, mock_store, mock_raptor) -> None:
        """Verify that input is passed as a generator (streaming)."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("Line 1\nLine 2\nLine 3")

        from typer.testing import CliRunner
        runner = CliRunner()

        # Run command
        # Use --no-verify to simplify
        result = runner.invoke(app, ["run", str(input_file), "--no-verify"])

        if result.exit_code != 0:
            print(result.stdout)
            print(result.stderr)

        assert result.exit_code == 0

        # Verify RaptorEngine.run was called
        mock_instance = mock_raptor.return_value
        assert mock_instance.run.called

        # Check argument type
        args, _ = mock_instance.run.call_args
        text_arg = args[0]

        # It should be an iterator/generator, not a string
        assert not isinstance(text_arg, str)
        assert hasattr(text_arg, "__next__") or hasattr(text_arg, "__iter__")

        # Verify content
        content = list(text_arg)
        assert content == ["Line 1\n", "Line 2\n", "Line 3"]
