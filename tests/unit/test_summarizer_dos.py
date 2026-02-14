from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from domain_models.constants import DEFAULT_MAX_INPUT_LENGTH
from matome.agents.summarizer import SummarizationAgent


@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig()


@pytest.fixture
def agent(config: ProcessingConfig) -> SummarizationAgent:
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="test_key"):
        agent = SummarizationAgent(config)
        agent.llm = MagicMock()
        return agent


def test_summarize_long_document_dos(agent: SummarizationAgent, config: ProcessingConfig) -> None:
    """
    Test protection against document length DoS.
    Max length is now checked against DEFAULT_MAX_INPUT_LENGTH (100,000).
    """
    # Create text exceeding limits
    # We construct safe text with spaces
    oversized_text = "a" * (DEFAULT_MAX_INPUT_LENGTH + 100)

    # Validation should fail BEFORE calling LLM
    with pytest.raises(ValueError, match="Input text exceeds maximum allowed length"):
        agent.summarize(oversized_text, config)

    # Verify LLM was NOT called
    if hasattr(agent.llm, "invoke"):
        agent.llm.invoke.assert_not_called()  # type: ignore
