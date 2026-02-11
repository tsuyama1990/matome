from matome.agents.strategies import (
    ActionStrategy,
    DIKWHierarchyStrategy,
    KnowledgeStrategy,
    RefinementStrategy,
    WisdomStrategy,
)
from matome.utils.prompts import (
    ACTION_PROMPT,
    KNOWLEDGE_PROMPT,
    WISDOM_PROMPT,
)


def test_action_strategy() -> None:
    strategy = ActionStrategy()
    chunks = ["Task 1", "Task 2"]
    prompt = strategy.create_prompt(chunks, current_level=1)

    assert ACTION_PROMPT.format(context="Task 1\n\nTask 2") in prompt
    assert strategy.parse_output("output") == "output"


def test_knowledge_strategy() -> None:
    strategy = KnowledgeStrategy()
    chunks = ["Concept A", "Concept B"]
    prompt = strategy.create_prompt(chunks, current_level=2)

    assert KNOWLEDGE_PROMPT.format(context="Concept A\n\nConcept B") in prompt


def test_wisdom_strategy() -> None:
    strategy = WisdomStrategy()
    chunks = ["Lesson 1", "Lesson 2"]
    prompt = strategy.create_prompt(chunks, current_level=3)

    assert WISDOM_PROMPT.format(context="Lesson 1\n\nLesson 2") in prompt


def test_dikw_hierarchy_strategy() -> None:
    strategy = DIKWHierarchyStrategy()
    chunks = ["Context"]

    # Level 1 -> Action
    prompt_l1 = strategy.create_prompt(chunks, current_level=1)
    assert "pragmatic Coach" in prompt_l1 or "Information" in prompt_l1

    # Level 2 -> Knowledge
    prompt_l2 = strategy.create_prompt(chunks, current_level=2)
    assert "Analyst structuring" in prompt_l2 or "Knowledge" in prompt_l2

    # Level 3 -> Wisdom
    prompt_l3 = strategy.create_prompt(chunks, current_level=3)
    assert "Philosopher" in prompt_l3 or "Wisdom" in prompt_l3

    # Level 4 -> Wisdom (default for high levels)
    prompt_l4 = strategy.create_prompt(chunks, current_level=4)
    assert "Philosopher" in prompt_l4 or "Wisdom" in prompt_l4


def test_refinement_strategy() -> None:
    instruction = "Make it simpler."
    strategy = RefinementStrategy(instruction)
    chunks = ["Original text"]
    prompt = strategy.create_prompt(chunks, current_level=1)

    assert instruction in prompt
    assert "Refine the following content" in prompt
    assert "Original text" in prompt
