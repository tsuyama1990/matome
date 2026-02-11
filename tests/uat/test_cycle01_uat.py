import pytest
from pydantic import ValidationError

from domain_models.manifest import SummaryNode, NodeMetadata
from domain_models.types import DIKWLevel
from matome.agents.summarizer import SummarizationAgent
from domain_models.config import ProcessingConfig
from matome.agents.strategies import PromptStrategy

# UAT Scenario 1.1: Metadata Validation
def test_uat_metadata_validation():
    """
    Scenario 1.1: Metadata Validation (The "Schema Check")
    Ensure that all new and existing nodes conform to the new metadata schema.
    """
    # 1. Valid Metadata
    valid_meta = NodeMetadata(dikw_level="wisdom")
    node = SummaryNode(
        id="valid_node",
        text="Valid Node",
        level=1,
        children_indices=[1],
        metadata=valid_meta
    )
    assert node.metadata.dikw_level == DIKWLevel.WISDOM

    # 2. Invalid Metadata (should raise ValidationError)
    with pytest.raises(ValidationError):
        NodeMetadata(dikw_level="super_wisdom")


# UAT Scenario 1.2: Strategy Injection
class PirateStrategy(PromptStrategy):
    """
    Mock Strategy for UAT Scenario 1.2.
    """
    def create_prompt(self, text: str, context: dict | None = None) -> str:
        return f"Summarize this like a pirate: {text}"


def test_uat_strategy_injection():
    """
    Scenario 1.2: Strategy Injection (The "Brain Swap")
    Confirm that SummarizationAgent effectively delegates prompt generation to the injected strategy.
    """
    config = ProcessingConfig(summarization_model="mock-model")

    # Instantiate with PirateStrategy
    strategy = PirateStrategy()
    agent = SummarizationAgent(config, strategy=strategy)

    # Mock LLM to inspect the prompt
    # We set mock_mode=False to use the injected LLM or force mock behavior differently?
    # Actually we can just mock the LLM instance directly.
    from unittest.mock import MagicMock
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
def test_uat_regression_safety():
    """
    Scenario 1.3: Regression Safety (The "Do No Harm")
    Ensure the standard SummarizationAgent still works exactly as before (BaseSummaryStrategy).
    """
    config = ProcessingConfig(summarization_model="mock-model")

    # Instantiate without strategy (should default to BaseSummaryStrategy)
    agent = SummarizationAgent(config)

    # Mock LLM
    from unittest.mock import MagicMock
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "Standard Summary"
    agent.llm = mock_llm

    # Call summarize
    input_text = "Hello World"
    agent.summarize(input_text)

    # Verify the prompt follows standard COD template
    from matome.utils.prompts import COD_TEMPLATE
    expected_prompt_start = COD_TEMPLATE.split("{")[0].strip()  # Get the start of the template

    call_args = mock_llm.invoke.call_args
    messages = call_args[0][0]
    prompt_sent = messages[0].content

    # Check if the prompt roughly matches the template structure
    # Since COD_TEMPLATE has {context}, we can check if template parts exist in prompt
    assert "Please generate a high-density summary" in prompt_sent
    assert input_text in prompt_sent
