from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from matome.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Matome: Long Context Summarization System" in result.stdout
    assert "run" in result.stdout
    assert "export" in result.stdout


@patch("matome.cli.RaptorEngine")
@patch("matome.cli.DiskChunkStore")
@patch("matome.cli.JapaneseTokenChunker")
@patch("matome.cli.EmbeddingService")
@patch("matome.cli.GMMClusterer")
@patch("matome.cli.SummarizationAgent")
@patch("matome.cli.VerifierAgent")
def test_cli_run_success(
    mock_verifier_cls: MagicMock,
    mock_summarizer_cls: MagicMock,
    mock_clusterer_cls: MagicMock,
    mock_embedder_cls: MagicMock,
    mock_chunker_cls: MagicMock,
    mock_store_cls: MagicMock,
    mock_raptor_cls: MagicMock,
) -> None:
    # Setup mocks
    mock_raptor_instance = mock_raptor_cls.return_value
    mock_tree = MagicMock()
    # Mock root node with concrete values to pass Pydantic validation in Exporter
    mock_tree.root_node.id = "root_id"
    mock_tree.root_node.text = "Root Summary"
    mock_tree.root_node.children_indices = [0, 1]

    # Also need to mock all_nodes if accessed
    mock_tree.all_nodes = {"root_id": mock_tree.root_node}

    mock_raptor_instance.run.return_value = mock_tree

    # Mock Store get_node to return dummy nodes
    mock_store_instance = mock_store_cls.return_value
    mock_node = MagicMock()
    mock_node.text = "Child Text"
    mock_store_instance.get_node.return_value = mock_node

    # Mock Verifier
    mock_verifier_instance = mock_verifier_cls.return_value
    mock_result = MagicMock()
    mock_result.score = 1.0
    mock_result.model_dump_json.return_value = "{}"
    mock_verifier_instance.verify.return_value = mock_result

    # Use isolated filesystem to create real file for Typer validation
    with runner.isolated_filesystem():
        Path("dummy.txt").write_text("Dummy text content")

        result = runner.invoke(
            app,
            ["run", "dummy.txt", "--output-dir", "results"],
            env={"SUMMARIZATION_MODEL": "gpt-4o"},
        )

        assert result.exit_code == 0
        assert "Starting Matome Pipeline" in result.stdout

        # Check if RaptorEngine.run was called
        mock_raptor_instance.run.assert_called_once()
        # Check if VerifierAgent was initialized (if verification enabled)
        mock_verifier_cls.assert_called_once()


@patch("matome.cli.export_to_markdown", return_value="MD Content")
@patch("matome.cli.ObsidianCanvasExporter")
def test_cli_run_success_with_exporters_mocked(
    mock_obs_cls: MagicMock,
    mock_md_func: MagicMock,
) -> None:
    # This is a cleaner version of the above test, patching everything
    with (
        patch("matome.cli.RaptorEngine") as mock_raptor_cls,
        patch("matome.cli.DiskChunkStore"),
        patch("matome.cli.JapaneseTokenChunker"),
        patch("matome.cli.EmbeddingService"),
        patch("matome.cli.GMMClusterer"),
        patch("matome.cli.SummarizationAgent"),
        patch("matome.cli.VerifierAgent") as mock_verifier_cls,
    ):
        mock_raptor_instance = mock_raptor_cls.return_value
        mock_tree = MagicMock()
        mock_tree.root_node.id = "root_id"
        mock_tree.root_node.text = "Summary"
        mock_tree.root_node.children_indices = []
        mock_raptor_instance.run.return_value = mock_tree

        mock_verifier_instance = mock_verifier_cls.return_value
        mock_verifier_instance.verify.return_value.score = 1.0
        mock_verifier_instance.verify.return_value.model_dump_json.return_value = "{}"

        with runner.isolated_filesystem():
            Path("dummy.txt").write_text("Dummy text content")

            result = runner.invoke(
                app,
                ["run", "dummy.txt", "--output-dir", "results"],
                env={"SUMMARIZATION_MODEL": "gpt-4o"},
            )

            assert result.exit_code == 0
            assert "Starting Matome Pipeline" in result.stdout

            mock_md_func.assert_called_once()
            mock_obs_cls.return_value.export.assert_called_once()


def test_cli_run_file_not_found() -> None:
    # We rely on Typer's argument validation
    # This runs in a temp dir where input file doesn't exist
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["run", "non_existent.txt"])

        # Typer/Click argument error exit code is 2
        assert result.exit_code == 2
