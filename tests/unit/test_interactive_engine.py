from unittest.mock import MagicMock, ANY, patch
import pytest
from domain_models.data_schema import NodeMetadata, DIKWLevel
from domain_models.manifest import SummaryNode, Chunk
from matome.engines.interactive_raptor import InteractiveRaptorEngine, RefinementAgent
from matome.agents.summarizer import SummarizationAgent
from matome.utils.store import DiskChunkStore
from matome.agents.strategies import WisdomStrategy, KnowledgeStrategy, InformationStrategy, RefinementStrategy, BaseSummaryStrategy

@pytest.fixture
def mock_store() -> MagicMock:
    return MagicMock(spec=DiskChunkStore)

@pytest.fixture
def mock_agent() -> MagicMock:
    agent = MagicMock(spec=SummarizationAgent)
    agent.strategy = MagicMock()

    config = MagicMock()
    config.max_input_length = 1000
    config.max_word_length = 100
    agent.config = config

    agent.llm = MagicMock()
    return agent

@pytest.fixture
def engine(mock_store: MagicMock, mock_agent: MagicMock) -> InteractiveRaptorEngine:
    return InteractiveRaptorEngine(store=mock_store, agent=mock_agent)

def test_get_node_chunk(engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test retrieving a Chunk."""
    chunk = Chunk(index=1, text="Chunk text", start_char_idx=0, end_char_idx=10, embedding=[0.1])
    mock_store.get_node.return_value = chunk

    result = engine.get_node("1")
    assert result == chunk
    mock_store.get_node.assert_called_with("1")

def test_get_node_summary(engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test retrieving a SummaryNode."""
    summary = SummaryNode(id="s1", text="Summary", level=1, children_indices=[1], metadata=NodeMetadata())
    mock_store.get_node.return_value = summary

    result = engine.get_node("s1")
    assert result == summary

def test_get_node_missing(engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test retrieving a missing node."""
    mock_store.get_node.return_value = None
    result = engine.get_node("missing")
    assert result is None

def test_refine_node_success(engine: InteractiveRaptorEngine, mock_store: MagicMock, mock_agent: MagicMock) -> None:
    """Test successfully refining a node."""
    original_node = SummaryNode(
        id="w1",
        text="Old Wisdom",
        level=1,
        children_indices=[1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM, refinement_history=[])
    )
    mock_store.get_node.return_value = original_node

    # We simulate the agent returning a new node.
    refined_node = SummaryNode(
        id="w1",
        text="Refined Wisdom",
        level=1,
        children_indices=[1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )

    instruction = "Make it better"

    with patch("matome.engines.interactive_raptor.RefinementAgent") as MockRefinementAgent:
        mock_temp_agent = MockRefinementAgent.return_value
        mock_temp_agent.summarize.return_value = refined_node

        result = engine.refine_node("w1", instruction)

        # Verify temp agent called correctly
        mock_temp_agent.summarize.assert_called_once()
        args, kwargs = mock_temp_agent.summarize.call_args
        assert kwargs['text'] == "Old Wisdom"
        context = kwargs['context']
        assert context['instruction'] == instruction

        # Verify result metadata update
        assert result.text == "Refined Wisdom"
        assert result.metadata.is_user_edited is True
        assert len(result.metadata.refinement_history) == 1
        assert result.metadata.refinement_history[0] == instruction

        # Verify persistence
        mock_store.add_summary.assert_called_once_with(result)

def test_refine_node_missing(engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test refining a missing node raises error."""
    mock_store.get_node.return_value = None
    with pytest.raises(ValueError, match="Node .* not found"):
        engine.refine_node("missing", "instr")

def test_refine_chunk_error(engine: InteractiveRaptorEngine, mock_store: MagicMock) -> None:
    """Test attempting to refine a raw Chunk raises TypeError."""
    chunk = Chunk(index=1, text="Raw", start_char_idx=0, end_char_idx=10, embedding=None)
    mock_store.get_node.return_value = chunk

    with pytest.raises(TypeError, match="Cannot refine a raw Chunk"):
        engine.refine_node("1", "instr")

def test_refine_node_strategy_selection(engine: InteractiveRaptorEngine, mock_store: MagicMock, mock_agent: MagicMock) -> None:
    """Test that the correct base strategy is selected based on DIKW level."""
    node = SummaryNode(
        id="k1",
        text="Knowledge",
        level=1,
        children_indices=[1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
    )
    mock_store.get_node.return_value = node

    with patch("matome.engines.interactive_raptor.RefinementAgent") as MockRefinementAgent:
        mock_temp_agent = MockRefinementAgent.return_value
        mock_temp_agent.summarize.return_value = SummaryNode(
            id="k1", text="New", level=1, children_indices=[], metadata=NodeMetadata()
        )

        engine.refine_node("k1", "instr")

        # Verify RefinementAgent was initialized with RefinementStrategy wrapping KnowledgeStrategy
        MockRefinementAgent.assert_called_once()
        call_args = MockRefinementAgent.call_args
        strategy_arg = call_args.kwargs.get('strategy')

        assert isinstance(strategy_arg, RefinementStrategy)
        assert isinstance(strategy_arg.base_strategy, KnowledgeStrategy)

def test_refinement_agent_filters_context() -> None:
    """Test that RefinementAgent filters 'instruction' from context before creating summary node."""
    strategy = MagicMock()
    strategy.parse_output.return_value = {"summary": "summary", "id": "1", "level": 1, "children_indices": []}

    config = MagicMock()
    config.max_input_length = 1000
    config.max_word_length = 100
    # Add valid string values for Pydantic validation in SummarizationAgent.__init__
    config.summarization_model = "gpt-4o-mini"
    config.llm_temperature = 0.5
    config.max_retries = 1

    agent = RefinementAgent(config, strategy)

    context = {"instruction": "fail me", "id": "1", "level": 1}

    # We allow the real call to happen, but verify it succeeds.
    # If "instruction" was not filtered, SummaryNode validation would fail.
    result = agent._create_summary_node("response", context, strategy)
    assert isinstance(result, SummaryNode)
    assert result.id == "1"

def test_refine_node_preserves_metadata_and_info_strategy(
    engine: InteractiveRaptorEngine, mock_store: MagicMock, mock_agent: MagicMock
) -> None:
    """Test refining an Information node and preserving cluster_id/type."""
    original_node = SummaryNode(
        id="i1",
        text="Old Info",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(
            dikw_level=DIKWLevel.INFORMATION,
            cluster_id=99,
            type="special"
        )
    )
    mock_store.get_node.return_value = original_node

    refined_node = SummaryNode(
        id="i1",
        text="New Info",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )

    with patch("matome.engines.interactive_raptor.RefinementAgent") as MockRefinementAgent:
        mock_temp = MockRefinementAgent.return_value
        mock_temp.summarize.return_value = refined_node

        result = engine.refine_node("i1", "instr")

        # Verify Strategy was InformationStrategy
        MockRefinementAgent.assert_called_once()
        strategy_arg = MockRefinementAgent.call_args.kwargs.get('strategy')
        assert strategy_arg is not None
        assert isinstance(strategy_arg.base_strategy, InformationStrategy)

        # Verify metadata preserved
        assert result.metadata.cluster_id == 99
        assert result.metadata.type == "special"

def test_refine_node_default_strategy(
    engine: InteractiveRaptorEngine, mock_store: MagicMock, mock_agent: MagicMock
) -> None:
    """Test refining a node with DATA level uses BaseSummaryStrategy."""
    original_node = SummaryNode(
        id="d1",
        text="Data",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.DATA)
    )
    mock_store.get_node.return_value = original_node

    with patch("matome.engines.interactive_raptor.RefinementAgent") as MockRefinementAgent:
        mock_temp = MockRefinementAgent.return_value
        mock_temp.summarize.return_value = original_node # dummy

        engine.refine_node("d1", "instr")

        strategy_arg = MockRefinementAgent.call_args.kwargs.get('strategy')
        assert strategy_arg is not None
        # BaseSummaryStrategy is used for DATA or others
        assert isinstance(strategy_arg.base_strategy, BaseSummaryStrategy)
