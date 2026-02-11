from unittest.mock import MagicMock

from domain_models.manifest import NodeMetadata, SummaryNode
from matome.engines.interactive import InteractiveRaptorEngine


def test_refine_node() -> None:
    """Test refining a node with new instructions."""
    store = MagicMock()
    summarizer = MagicMock()
    embedder = MagicMock()
    config = MagicMock()

    engine = InteractiveRaptorEngine(store, summarizer, embedder, config)

    node = SummaryNode(
        id="1",
        text="Old Text",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(),
    )
    store.get_node.return_value = node
    summarizer.summarize.return_value = "New Text"
    embedder.embed_strings.return_value = [[0.1, 0.2]]

    updated_node = engine.refine_node("1", "Make it better")

    assert updated_node.text == "New Text"
    assert updated_node.metadata.is_user_edited is True
    assert "Make it better" in updated_node.metadata.refinement_history
    assert updated_node.embedding == [0.1, 0.2]

    store.add_summaries.assert_called()
    summarizer.summarize.assert_called()
    # check strategy arg
    call_args = summarizer.summarize.call_args
    assert call_args.kwargs["strategy"].instructions == "Make it better"
