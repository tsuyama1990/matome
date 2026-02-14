import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from collections.abc import Generator

import pytest
from typer.testing import CliRunner

from domain_models.config import ProcessingConfig
from matome.cli import app

runner = CliRunner()


@pytest.fixture
def mock_store() -> Generator[MagicMock, None, None]:
    with patch("matome.cli.DiskChunkStore") as mock:
        mock_instance = mock.return_value
        mock_instance.__enter__.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_components() -> Generator[tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock], None, None]:
    with patch("matome.cli._initialize_components") as mock:
        chunker = MagicMock()
        chunker.split_text.return_value = []
        embedder = MagicMock()
        clusterer = MagicMock()
        summarizer = MagicMock()
        verifier = MagicMock()

        mock.return_value = (chunker, embedder, clusterer, summarizer, verifier)
        yield (chunker, embedder, clusterer, summarizer, verifier)


@pytest.fixture
def mock_raptor_run() -> Generator[MagicMock, None, None]:
    with patch("matome.cli.RaptorEngine.run") as mock:
        mock.return_value = MagicMock()
        yield mock


def test_cli_run_success(
    mock_store: MagicMock,
    mock_components: tuple[MagicMock, ...],
    mock_raptor_run: MagicMock,
    tmp_path: Path
) -> None:
    """Test successful run of the pipeline."""
    input_file = tmp_path / "input.txt"
    input_file.write_text("Test content", encoding="utf-8")

    result = runner.invoke(app, ["run", str(input_file), "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "Done!" in result.stdout
    mock_raptor_run.assert_called_once()


def test_cli_run_file_not_found() -> None:
    """Test behavior when input file does not exist."""
    result = runner.invoke(app, ["run", "nonexistent.txt"])
    # Typer returns 2 for usage/argument errors
    assert result.exit_code == 2
    # Output contains the error message (stderr is captured)
    assert "does not exist" in result.output


def test_cli_run_file_too_large(tmp_path: Path) -> None:
    """Test error handling for large files."""
    input_file = tmp_path / "large.txt"
    input_file.write_text("a", encoding="utf-8")

    # Mock os.stat which is called by Path.stat()
    with patch("os.stat") as mock_stat:
        mock_stat.return_value.st_size = 1024 * 1024 * 1024 * 2  # 2GB
        # Ensure st_mode is set to avoid issues if stat result is used elsewhere (e.g. is_file check)
        mock_stat.return_value.st_mode = 33188 # Regular file

        result = runner.invoke(app, ["run", str(input_file)])

        assert result.exit_code == 1
        # Check result.output (stdout + stderr)
        assert "File too large" in result.output


def test_initialize_components() -> None:
    """Test component initialization helper."""
    with patch("matome.config.get_openrouter_api_key", return_value="mock"):
        from matome.cli import _initialize_components
        config = ProcessingConfig()
        with patch("matome.cli.JapaneseTokenChunker"), patch("matome.cli.EmbeddingService"), patch("matome.cli.GMMClusterer"):
             components = _initialize_components(config)
             assert len(components) == 5
