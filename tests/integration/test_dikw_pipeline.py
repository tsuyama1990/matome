from unittest.mock import MagicMock

import pytest
from langchain_core.messages import BaseMessage

from domain_models.config import ProcessingConfig
from domain_models.data_schema import DIKWLevel
from matome.agents.strategies import (
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)
from matome.agents.summarizer import SummarizationAgent


@pytest.fixture
def mock_llm_response() -> MagicMock:
    """Mock LLM response."""
    llm = MagicMock()
    # Mock invoke method
    message = BaseMessage(content="Mocked Summary", type="ai")
    llm.invoke.return_value = message
    return llm


@pytest.fixture
def config() -> ProcessingConfig:
    """Processing config fixture."""
    return ProcessingConfig()


def test_wisdom_pipeline(mock_llm_response: MagicMock, config: ProcessingConfig) -> None:
    """Test full pipeline with WisdomStrategy."""
    strategy = WisdomStrategy()
    agent = SummarizationAgent(config, strategy=strategy, llm=mock_llm_response)

    # Set up mock response content
    mock_llm_response.invoke.return_value = BaseMessage(content="Life is suffering.", type="ai")

    context = {"id": "test-id", "level": 1, "children_indices": []}
    node = agent.summarize("Some text", context=context)

    assert node.text == "Life is suffering."
    assert node.metadata.dikw_level == DIKWLevel.WISDOM

    # Verify prompt content
    args, _ = mock_llm_response.invoke.call_args
    prompt_text = args[0][0].content
    assert "aphorism" in prompt_text.lower()


def test_knowledge_pipeline(mock_llm_response: MagicMock, config: ProcessingConfig) -> None:
    """Test full pipeline with KnowledgeStrategy."""
    strategy = KnowledgeStrategy()
    agent = SummarizationAgent(config, strategy=strategy, llm=mock_llm_response)

    # Set up mock response content
    mock_llm_response.invoke.return_value = BaseMessage(content="## Mental Model", type="ai")

    context = {"id": "test-id", "level": 1, "children_indices": []}
    node = agent.summarize("Some text", context=context)

    assert node.text == "## Mental Model"
    assert node.metadata.dikw_level == DIKWLevel.KNOWLEDGE

    # Verify prompt content
    args, _ = mock_llm_response.invoke.call_args
    prompt_text = args[0][0].content
    assert "mental models" in prompt_text.lower()


def test_information_pipeline(mock_llm_response: MagicMock, config: ProcessingConfig) -> None:
    """Test full pipeline with InformationStrategy."""
    strategy = InformationStrategy()
    agent = SummarizationAgent(config, strategy=strategy, llm=mock_llm_response)

    # Set up mock response content
    mock_llm_response.invoke.return_value = BaseMessage(content="- [ ] Do X", type="ai")

    context = {"id": "test-id", "level": 1, "children_indices": []}
    node = agent.summarize("Some text", context=context)

    assert node.text == "- [ ] Do X"
    assert node.metadata.dikw_level == DIKWLevel.INFORMATION

    # Verify prompt content
    args, _ = mock_llm_response.invoke.call_args
    prompt_text = args[0][0].content
    assert "checklist" in prompt_text.lower()
