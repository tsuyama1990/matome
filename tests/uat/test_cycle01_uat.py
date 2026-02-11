from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from domain_models.manifest import SummaryNode
from domain_models.metadata import DIKWLevel, NodeMetadata
from matome.agents.strategies import PromptStrategy
from matome.agents.summarizer import SummarizationAgent


def test_uat_c01_01_metadata_check() -> None:
    """
    Scenario C01-01: Data Model Robustness
    Verify preservation of DIKW metadata and backward compatibility.
    """
    # 1. Positive Test: Create Wisdom node, serialize, deserialize
    node = SummaryNode(
        id="test_wisdom",
        text="Wisdom Text",
        level=1,
        children_indices=[0],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM),
    )
    json_data = node.model_dump_json()
    loaded_node = SummaryNode.model_validate_json(json_data)
    assert loaded_node.metadata.dikw_level == DIKWLevel.WISDOM

    # 2. Migration Test: Legacy dictionary
    legacy_data = {
        "id": "legacy",
        "text": "text",
        "level": 1,
        "children_indices": [0],
        "metadata": {"source": "file.txt"},
    }
    # Using model_validate (from dict) instead of json
    legacy_node = SummaryNode.model_validate(legacy_data)
    assert legacy_node.metadata.dikw_level == DIKWLevel.DATA
    assert legacy_node.metadata.source == "file.txt"  # type: ignore


class PirateStrategy(PromptStrategy):
    """Custom strategy for UAT."""

    def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
        return "Ahoy matey: " + " ".join(context_chunks)

    def parse_output(self, llm_output: str) -> str:
        return llm_output


def test_uat_c01_02_strategy_injection() -> None:
    """
    Scenario C01-02: Strategy Injection
    Verify default behavior and custom strategy injection.
    """
    config = ProcessingConfig()

    # 1. Default Strategy
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        _ = SummarizationAgent(config)
        # Verification implies no crash and default behavior (covered by unit tests)

    # 2. Custom Strategy
    strategy = PirateStrategy()
    with patch("matome.agents.summarizer.get_openrouter_api_key", return_value="mock"):
        agent_custom = SummarizationAgent(config, prompt_strategy=strategy)
        agent_custom.mock_mode = False
        agent_custom.llm = MagicMock()
        llm_mock = agent_custom.llm
        llm_mock.invoke.return_value = AIMessage(content="Treasure found")

        agent_custom.summarize("map", config)

        args, _ = llm_mock.invoke.call_args
        prompt = args[0][0].content
        assert prompt.startswith("Ahoy matey")
