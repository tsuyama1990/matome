
from domain_models.data_schema import DIKWLevel
from matome.strategies import (
    BaseSummaryStrategy,
    DefaultStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)


class TestStrategies:
    def test_base_strategy(self) -> None:
        strategy = BaseSummaryStrategy()
        text = "Hello world"

        # Test format_prompt
        prompt = strategy.format_prompt(text)
        assert "Summarize the following text" in prompt
        assert text in prompt

        # Test instruction
        context = {"instruction": "Make it shorter"}
        prompt_with_instr = strategy.format_prompt(text, context)
        assert "User Instruction: Make it shorter" in prompt_with_instr

        # Test parse_output
        output = strategy.parse_output("Summary")
        assert output["text"] == "Summary"
        assert output["metadata"].dikw_level == DIKWLevel.DATA

    def test_default_strategy(self) -> None:
        strategy = DefaultStrategy()
        text = "Hello world"

        prompt = strategy.format_prompt(text)
        assert "generate a high-density summary" in prompt # COD template part

        context = {"instruction": "Add details"}
        prompt_with_instr = strategy.format_prompt(text, context)
        assert "User Instruction: Add details" in prompt_with_instr

        output = strategy.parse_output("Summary")
        assert output["metadata"].dikw_level == DIKWLevel.DATA

    def test_wisdom_strategy(self) -> None:
        strategy = WisdomStrategy()
        text = "Complex philosophy"

        prompt = strategy.format_prompt(text)
        assert "**Wisdom** (L1)" in prompt
        assert "Aphorism" in prompt

        output = strategy.parse_output("Wise saying")
        assert output["metadata"].dikw_level == DIKWLevel.WISDOM

    def test_knowledge_strategy(self) -> None:
        strategy = KnowledgeStrategy()
        text = "System mechanics"

        prompt = strategy.format_prompt(text)
        assert "**Knowledge** (L2)" in prompt
        assert "frameworks" in prompt

        output = strategy.parse_output("Explanation")
        assert output["metadata"].dikw_level == DIKWLevel.KNOWLEDGE

    def test_information_strategy(self) -> None:
        strategy = InformationStrategy()
        text = "How to do X"

        prompt = strategy.format_prompt(text)
        assert "**Information** (L3)" in prompt
        assert "Actionable steps" in prompt

        output = strategy.parse_output("Steps")
        assert output["metadata"].dikw_level == DIKWLevel.INFORMATION
