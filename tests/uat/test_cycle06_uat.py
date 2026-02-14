import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from typer.testing import CliRunner

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster
from matome.agents.verifier import VerifierAgent
from matome.cli import app

runner = CliRunner()


@pytest.fixture
def sample_text_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "sample.txt"
    file_path.write_text(
        "This is a sample document for UAT testing. It contains some text about planets. There are 8 planets in the solar system.",
        encoding="utf-8",
    )
    return file_path


@pytest.fixture
def uat_config() -> ProcessingConfig:
    return ProcessingConfig(max_tokens=20, chunk_buffer_size=5)


def test_scenario_16_hallucination_detection(uat_config: ProcessingConfig) -> None:
    """
    Scenario 16: Hallucination Detection.
    Goal: Ensure the system flags unsupported claims.
    """
    # Arrange
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content=json.dumps(
            {
                "score": 0.5,
                "details": [
                    {
                        "claim": "There are 5 planets.",
                        "verdict": "Contradicted",
                        "reasoning": "Source says 8.",
                    }
                ],
                "unsupported_claims": ["There are 5 planets."],
                "model_name": "mock-model",
            }
        )
    )

    agent = VerifierAgent(uat_config, llm=mock_llm)
    summary = "There are 5 planets."
    source = "There are 8 planets in the solar system."

    # Act
    result = agent.verify(summary, source)

    # Assert
    assert result.score < 1.0
    assert "There are 5 planets." in result.unsupported_claims
    assert result.details[0].verdict == "Contradicted"


def test_scenario_17_cli_usability() -> None:
    """
    Scenario 17: CLI Usability Check.
    Goal: Ensure the command-line tool is intuitive and informative.
    """
    # Check help
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
    assert "run" in result.stdout

    # Check error handling for missing file
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["run", "missing.txt"])
        assert result.exit_code != 0
        # Wait, typer might catch exceptions and print to stderr.
        # But we assert exit code is not 0 (failure).


# Scenario 18: Use partial real components (Chunker) and mocked LLMs/Embedder/Clusterer
# We mock Clusterer because real clustering with 1 item might be unstable depending on implementation details
# and we want to test orchestration.
@patch("matome.cli._validate_output_dir")
# Use REAL JapaneseTokenChunker (not patched)
@patch("matome.cli.GMMClusterer")
@patch("matome.cli.SummarizationAgent")
@patch("matome.cli.VerifierAgent")
@patch("matome.cli.EmbeddingService")
def test_scenario_18_full_e2e_pipeline_partial_real(
    mock_embedder_cls: MagicMock,
    mock_verifier_cls: MagicMock,
    mock_summarizer_cls: MagicMock,
    mock_clusterer_cls: MagicMock,
    # mock_chunker_cls: MagicMock, # Not mocked
    mock_validate_dir: MagicMock,
    sample_text_file: Path,
    tmp_path: Path,
) -> None:
    """
    Scenario 18: Partial End-to-End Test.
    Goal: Verify the entire workflow from ingestion to export using some real components.
    We use real Chunker, but mock Embedder, Clusterer, and LLMs for determinism.
    """
    output_dir = tmp_path / "uat_results"

    # 1. Embedder Setup
    mock_embedder_instance = mock_embedder_cls.return_value

    def mock_embed_chunks(chunks: list[Chunk]) -> Iterator[Chunk]:
        for c in chunks:
            c.embedding = [0.1] * 10
            yield c

    mock_embedder_instance.embed_chunks.side_effect = mock_embed_chunks
    mock_embedder_instance.embed_strings.return_value = [[0.1] * 10]

    # 2. Clusterer Setup
    mock_clusterer_instance = mock_clusterer_cls.return_value

    # IMPORTANT: cluster_nodes MUST consume the generator to trigger store writes in RaptorEngine
    def cluster_side_effect(embeddings: Any, config: Any) -> list[Cluster]:
        for _ in embeddings:
            pass
        # Return 1 cluster for the chunk(s)
        return [Cluster(id=0, level=0, node_indices=[0])]

    mock_clusterer_instance.cluster_nodes.side_effect = cluster_side_effect

    # 3. Summarizer Setup
    mock_summarizer_instance = mock_summarizer_cls.return_value
    mock_summarizer_instance.summarize.return_value = "Summary of cluster."

    # 4. Verifier Setup
    mock_verifier_instance = mock_verifier_cls.return_value
    mock_result = MagicMock()
    mock_result.score = 1.0
    mock_result.model_dump_json.return_value = "{}"
    mock_verifier_instance.verify.return_value = mock_result

    # Act
    result = runner.invoke(
        app,
        [
            "run",
            str(sample_text_file),
            "--output-dir",
            str(output_dir),
            "--max-tokens",
            "100", # Enough for the sample text
        ],
    )

    # Assert
    assert result.exit_code == 0
    assert "Tree construction complete" in result.stdout
    assert "Verification Score" in result.stdout

    assert (output_dir / "summary_all.md").exists()
    assert (output_dir / "chunks.db").exists()
