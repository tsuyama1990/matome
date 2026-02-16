import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from matome.agents.verifier import VerifierAgent


@pytest.fixture
def mock_llm_chain() -> MagicMock:
    llm = MagicMock()
    # Mock successful verification response
    response_data = {
        "score": 0.8,
        "details": [
            {"claim": "Claim 1", "verdict": "Supported", "reasoning": "Reason 1"},
            {"claim": "Claim 2", "verdict": "Unsupported", "reasoning": "Reason 2"},
        ],
        "unsupported_claims": ["Claim 2"],
    }
    llm.invoke.return_value = AIMessage(content=json.dumps(response_data))
    return llm


def test_verification_integration_flow(mock_llm_chain: MagicMock) -> None:
    """
    Test the verification agent integrated with config and mocked LLM.
    """
    config = ProcessingConfig(verification_model="openai/gpt-4o")
    agent = VerifierAgent(config, llm=mock_llm_chain)

    summary = "Claim 1. Claim 2."
    source = "Source text supporting Claim 1 but not Claim 2."

    result = agent.verify(summary, source)

    assert result.score == 0.8
    assert len(result.details) == 2
    assert "Claim 2" in result.unsupported_claims
    assert result.model_name == "openai/gpt-4o"
