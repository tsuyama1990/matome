from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from domain_models.config import ProcessingConfig
from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.agents.strategies import PromptStrategy
from matome.agents.summarizer import SummarizationAgent


# UAT Scenario 1.1: Metadata Validation
def test_uat_metadata_validation() -> None:
    """
    Scenario 1.1: Metadata Validation (The "Schema Check")
    Ensure that all new and existing nodes conform to the new metadata schema.
    """
    # 1. Valid Metadata
    meta = NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    # 2. Assign to Node
    node = SummaryNode(
        id="valid_node",
        text="Valid Node Content",
        level=1,
        children_indices=[1],
        metadata=meta
    )
    # Verify content and structure
    assert node.text == "Valid Node Content"
    assert node.level == 1
    assert node.children_indices == [1]
    assert node.metadata.dikw_level == DIKWLevel.WISDOM

    # 3. Invalid Metadata (should raise ValidationError)
    with pytest.raises(ValidationError):
        NodeMetadata(dikw_level="super_wisdom")  # type: ignore[arg-type]


# UAT Scenario 1.2: Strategy Injection
class PirateStrategy:
    """
    Mock Strategy for UAT Scenario 1.2.
    """
    def create_prompt(self, text: str | list[str], context: dict[str, Any] | None = None) -> str:
        if isinstance(text, list):
            text = " ".join(text)
        return f"Summarize this like a pirate: {text}"


def test_uat_strategy_injection() -> None:
    """
    Scenario 1.2: Strategy Injection (The "Brain Swap")
    Confirm that SummarizationAgent effectively delegates prompt generation to the injected strategy.
    """
    # Use valid model name
    config = ProcessingConfig(summarization_model="gpt-4o")

    # Instantiate with PirateStrategy
    strategy = PirateStrategy()
    agent = SummarizationAgent(config, strategy=strategy)

    # Mock LLM to inspect the prompt
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "Yarrr!"
    agent.llm = mock_llm

    # Call summarize
    input_text = "Hello World"
    agent.summarize(input_text)

    # Verify the prompt sent to LLM starts with "Summarize this like a pirate"
    call_args = mock_llm.invoke.call_args
    assert call_args, "LLM was not called"
    messages = call_args[0][0]
    prompt_sent = messages[0].content

    assert prompt_sent.startswith("Summarize this like a pirate")
    assert input_text in prompt_sent


# UAT Scenario 1.3: Regression Safety
def test_uat_regression_safety() -> None:
    """
    Scenario 1.3: Regression Safety (The "Do No Harm")
    Ensure the standard SummarizationAgent still works exactly as before (BaseSummaryStrategy).
    """
    # Use valid model name
    config = ProcessingConfig(summarization_model="gpt-4o")

    # Instantiate without strategy (should default to BaseSummaryStrategy)
    agent = SummarizationAgent(config)

    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "Standard Summary"
    agent.llm = mock_llm

    # Call summarize
    input_text = "Hello World"
    agent.summarize(input_text)

    # Verify the prompt follows standard COD template
    call_args = mock_llm.invoke.call_args
    messages = call_args[0][0]
    prompt_sent = messages[0].content

    # Check if the prompt roughly matches the template structure
    # Since COD_TEMPLATE has {context}, we can check if template parts exist in prompt
    assert "Please generate a high-density summary" in prompt_sent
    assert input_text in prompt_sent
