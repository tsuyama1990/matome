import pytest
from unittest.mock import MagicMock
from domain_models.manifest import SummaryNode
from domain_models.metadata import DIKWLevel, NodeMetadata
from matome.agents.summarizer import SummarizationAgent
from matome.agents.strategies import BaseSummaryStrategy
from domain_models.config import ProcessingConfig

def test_uat_c01_01_data_model_robustness() -> None:
    """
    Scenario ID: C01-01 (Data Model Robustness)
    Objective: Verify that the new NodeMetadata schema correctly handles data integrity and backward compatibility.
    """
    # 1. Positive Test
    node_meta = NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    assert node_meta.dikw_level == DIKWLevel.WISDOM

    # 2. Serialization check
    json_str = node_meta.model_dump_json()
    assert "wisdom" in json_str
    restored = NodeMetadata.model_validate_json(json_str)
    assert restored.dikw_level == DIKWLevel.WISDOM

    # 3. Migration Test
    # Create a dictionary mimicking an old node: {'text': '...', 'metadata': {'source': 'file.txt'}}
    # Pass this to SummaryNode. Verify that node.metadata.dikw_level defaults to 'data' and the source field is preserved.
    node_data = {
        "id": "test_id",
        "text": "test text",
        "level": 1,
        "children_indices": [0],
        "metadata": {"source": "file.txt"}
    }
    node = SummaryNode(**node_data)
    assert node.metadata.dikw_level == DIKWLevel.DATA
    assert getattr(node.metadata, "source") == "file.txt"


def test_uat_c01_02_strategy_injection() -> None:
    """
    Scenario ID: C01-02 (Strategy Injection)
    Objective: Verify that the SummarizationAgent functionality remains unchanged while using the new Strategy pattern.
    """
    config = ProcessingConfig()

    # 1. Initialize SummarizationAgent without arguments (should default to BaseStrategy)
    # Using mock LLM to avoid API call
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="DEFAULT SUMMARY")

    agent_default = SummarizationAgent(config=config, llm=mock_llm)
    # This assumes we modify Agent to accept prompt_strategy=None by default
    # and internally sets it to BaseSummaryStrategy

    # Run agent.summarize
    summary = agent_default.summarize("test text")
    assert summary == "DEFAULT SUMMARY"

    # Verify default strategy was used -> BaseSummaryStrategy uses COD template
    # We inspect the call args to see if COD template was used
    # Messages is the first argument to invoke
    args, _ = mock_llm.invoke.call_args
    assert "high-density summary" in args[0][0].content.lower()

    # 2. Initialize SummarizationAgent with a custom TestStrategy
    class PirateStrategy:
        def create_prompt(self, context_chunks: list[str], current_level: int) -> str:
            return "Ahoy matey: " + " ".join(context_chunks)

        def parse_output(self, llm_output: str) -> str:
            return "PIRATE SAYS: " + llm_output

    pirate_strategy = PirateStrategy()

    # Reset mock
    mock_llm.reset_mock()
    mock_llm.invoke.return_value = MagicMock(content="TREASURE")

    # Mypy will complain because prompt_strategy arg is not yet in init signature
    # and PirateStrategy might not satisfy Protocol yet (if Protocol is strictly checked and imports fail).
    agent_pirate = SummarizationAgent(config=config, llm=mock_llm, prompt_strategy=pirate_strategy) # type: ignore[call-arg, arg-type]

    summary_pirate = agent_pirate.summarize("Island")

    # Verify custom prompt
    args, _ = mock_llm.invoke.call_args
    assert "Ahoy matey: Island" in args[0][0].content

    # Verify custom parsing
    assert summary_pirate == "PIRATE SAYS: TREASURE"
