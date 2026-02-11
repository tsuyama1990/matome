import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from domain_models.config import ProcessingConfig
from domain_models.manifest import SummaryNode
from domain_models.metadata import DIKWLevel, NodeMetadata
from matome.agents.summarizer import SummarizationAgent
from matome.engines.interactive import InteractiveRaptorEngine
from matome.utils.store import DiskChunkStore


@pytest.fixture
def store() -> Generator[DiskChunkStore, None, None]:
    """Create a temporary DiskChunkStore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = DiskChunkStore(db_path)
        yield store
        store.close()


@pytest.fixture
def agent() -> SummarizationAgent:
    """Create a mocked SummarizationAgent."""
    config = ProcessingConfig()
    agent = SummarizationAgent(config)
    agent.llm = MagicMock()
    # Mock invoke to return a predictable string
    agent.llm.invoke.return_value = AIMessage(content="Refined Content")
    # Mock mock_mode to False so it uses the mock LLM
    agent.mock_mode = False
    return agent


def test_refine_node(store: DiskChunkStore, agent: SummarizationAgent) -> None:
    """Test refining a node."""
    # Setup: Add a node to the store
    node_id = "node-1"
    original_text = "Original Text"
    node = SummaryNode(
        id=node_id,
        text=original_text,
        level=1,
        children_indices=[0],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )
    store.add_summary(node)

    # Initialize Engine
    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(store, agent, config)

    # Execute Refinement
    instruction = "Make it better"
    updated_node = engine.refine_node(node_id, instruction)

    # Verify
    assert updated_node.id == node_id
    assert updated_node.text == "Refined Content"
    assert updated_node.metadata.is_user_edited is True
    assert instruction in updated_node.metadata.refinement_history

    # Verify Persistence
    stored_node = store.get_node(node_id)
    assert isinstance(stored_node, SummaryNode)
    assert stored_node.text == "Refined Content"
    assert stored_node.metadata.is_user_edited is True


def test_refine_node_not_found(store: DiskChunkStore, agent: SummarizationAgent) -> None:
    """Test error when node not found."""
    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(store, agent, config)

    with pytest.raises(ValueError, match="not found"):
        engine.refine_node("non-existent", "instr")


def test_refine_node_store_failure(store: DiskChunkStore, agent: SummarizationAgent) -> None:
    """Test error handling when store update fails."""
    # Setup: Add a node
    node_id = "node-failure"
    node = SummaryNode(
        id=node_id, text="Text", level=1, children_indices=[0],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )
    store.add_summary(node)

    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(store, agent, config)

    # Mock store.add_summary to raise Exception
    # We use patch.object for cleaner and safer mocking that mypy accepts
    with patch.object(store, "add_summary", side_effect=Exception("DB Error")):
        with pytest.raises(Exception, match="DB Error"):
            engine.refine_node(node_id, "instruction")
