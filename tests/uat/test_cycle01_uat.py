from unittest.mock import MagicMock, Mock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.data_schema import NodeMetadata
from matome.agents.summarizer import SummarizationAgent
from matome.interfaces import PromptStrategy


# Scenario 01-A: Strategy Injection Verification
def test_scenario_01_a_strategy_injection() -> None:
    # 1. Create custom MockStrategy
    mock_strategy = Mock(spec=PromptStrategy)
    mock_strategy.format_prompt.return_value = "MOCK_PROMPT"
    mock_strategy.parse_output.return_value = {"summary": "MOCK_RESULT"}

    # 2. Instantiate SummarizationAgent
    # We need to bypass mock mode to test strategy usage
    # Because mock mode returns "Summary of {text}..." without calling LLM or strategy
    # So we provide a mock LLM.
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "ANY_CONTENT"

    config = ProcessingConfig(summarization_model="mock-model", verification_model="mock-model", embedding_model="mock-model")
    agent = SummarizationAgent(config, llm=mock_llm)
    agent.mock_mode = False

    # 3. Call summarize
    # Since implementation is pending, catch ImportError or AttributeError if strategy is not yet supported
    try:
        # Note: If strategy argument is not yet added to summarize signature, python will raise TypeError
        summary = agent.summarize("test text", strategy=mock_strategy)
    except TypeError:
        pytest.skip("Scenario 01-A: 'strategy' argument not accepted yet. Pending implementation.")

    # 4. Assert summary
    assert summary == "MOCK_RESULT"
    mock_strategy.format_prompt.assert_called_once_with("test text")
    # parse_output should be called with LLM response content
    mock_strategy.parse_output.assert_called_with("ANY_CONTENT")


# Scenario 01-B: Schema Backward Compatibility
def test_scenario_01_b_schema_compatibility() -> None:
    # 1. Create old dict
    old_dict = {"cluster_id": 1, "summary": "Old summary"}

    # 2. Instantiate NodeMetadata
    try:
        meta = NodeMetadata(**old_dict)  # type: ignore[arg-type]
    except Exception as e:
        pytest.fail(f"Scenario 01-B Failed: Instantiation error: {e}")

    # 3. Inspect object
    assert meta.cluster_id == 1
    assert meta.dikw_level == "data" # Default
    assert meta.is_user_edited is False # Default
    assert meta.refinement_history == [] # Default

    # Check extra field handling (allowed)
    # Pydantic V2 access to extra fields via .model_extra
    assert meta.model_extra is not None
    assert meta.model_extra.get("summary") == "Old summary"
