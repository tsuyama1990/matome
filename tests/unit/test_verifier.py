import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from domain_models.verification import VerificationResult
from matome.agents.verifier import VerifierAgent
from matome.exceptions import VerificationError


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    # Mock invoke to return an AIMessage with JSON content
    mock_response = {
        "score": 1.0,
        "details": [
            {"claim": "The sky is blue.", "verdict": "Supported", "reasoning": "Text says so."}
        ],
        "unsupported_claims": [],
    }
    llm.invoke.return_value = AIMessage(content=json.dumps(mock_response))
    return llm


@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig()


def test_verifier_initialization(config: ProcessingConfig) -> None:
    # Test initialization with and without LLM
    agent = VerifierAgent(config)
    assert agent.config == config


def test_verify_success(config: ProcessingConfig, mock_llm: MagicMock) -> None:
    agent = VerifierAgent(config, llm=mock_llm)

    summary = "The sky is blue."
    source = "The sky is blue and the grass is green."

    result = agent.verify(summary, source)

    assert isinstance(result, VerificationResult)
    assert result.score == 1.0
    assert len(result.details) == 1
    assert result.details[0].claim == "The sky is blue."
    assert result.details[0].verdict == "Supported"
    assert not result.unsupported_claims


def test_verify_unsupported(config: ProcessingConfig, mock_llm: MagicMock) -> None:
    agent = VerifierAgent(config, llm=mock_llm)

    # Mock a failure case
    mock_response = {
        "score": 0.5,
        "details": [
            {
                "claim": "The sky is green.",
                "verdict": "Contradicted",
                "reasoning": "Text says blue.",
            }
        ],
        "unsupported_claims": ["The sky is green."],
    }
    mock_llm.invoke.return_value = AIMessage(content=json.dumps(mock_response))

    summary = "The sky is green."
    source = "The sky is blue."

    result = agent.verify(summary, source)

    assert result.score == 0.5
    assert len(result.unsupported_claims) == 1
    assert result.unsupported_claims[0] == "The sky is green."


def test_verify_malformed_json(config: ProcessingConfig, mock_llm: MagicMock) -> None:
    agent = VerifierAgent(config, llm=mock_llm)

    # Mock invalid JSON
    mock_llm.invoke.return_value = AIMessage(content="This is not JSON.")

    with pytest.raises(VerificationError):
        agent.verify("summary", "source")
