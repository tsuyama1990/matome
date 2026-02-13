import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from matome.cli import app

runner = CliRunner()

def test_serve_command_help():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    # We check if help text contains description.
    # Exact wording depends on implementation.
    assert "Start the Matome Interactive GUI" in result.stdout or "serve" in result.stdout

@patch("matome.cli.pn.serve")
@patch("matome.cli.InteractiveSession")
@patch("matome.cli.MatomeCanvas")
@patch("matome.cli.DiskChunkStore")
@patch("matome.cli.InteractiveRaptorEngine")
@patch("matome.cli.SummarizationAgent")
def test_serve_command_execution(
    MockSummarizationAgent,
    MockInteractiveRaptorEngine,
    MockDiskChunkStore,
    MockMatomeCanvas,
    MockInteractiveSession,
    mock_pn_serve
):
    # Setup mocks
    mock_canvas = MockMatomeCanvas.return_value
    mock_canvas.layout = MagicMock()

    # Create a dummy file for the argument
    with runner.isolated_filesystem():
        with open("chunks.db", "w") as f:
            f.write("dummy")

        result = runner.invoke(app, ["serve", "chunks.db"])

        assert result.exit_code == 0

        # Verify initializations
        MockDiskChunkStore.assert_called_once()
        MockInteractiveRaptorEngine.assert_called_once()
        # Session and Canvas are created inside the factory, so they might be called multiple times if serve calls the factory.
        # But here serve is mocked, so it won't call the factory unless we do.
        # So mocks are NOT called yet for Session/Canvas.
        MockInteractiveSession.assert_not_called()
        MockMatomeCanvas.assert_not_called()

        # Verify serve called with factory function
        mock_pn_serve.assert_called_once()
        args, kwargs = mock_pn_serve.call_args
        factory_func = args[0]
        assert callable(factory_func)
        assert kwargs['port'] == 5006

        # Call factory to verify Session/Canvas creation
        layout = factory_func()
        assert layout == mock_canvas.layout
        MockInteractiveSession.assert_called_once()
        MockMatomeCanvas.assert_called_once()
