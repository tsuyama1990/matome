from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import NodeMetadata, SummaryNode
from matome.engines.interactive_raptor import InteractiveRaptorEngine


def test_refine_node_missing_children() -> None:
    """Test that refining a node with no children raises ValueError."""
    store = MagicMock()
    summarizer = MagicMock()
    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(store, summarizer, config)

    node = SummaryNode(
        id="s1",
        text="Summary",
        level=1,
        children_indices=[1, 2],
        metadata=NodeMetadata()
    )

    # Store returns the node itself
    store.get_node.side_effect = lambda nid: node if nid == "s1" else None

    # But returns None for children (simulating missing/deleted children)

    with pytest.raises(ValueError, match="Node s1 has no accessible children. Cannot refine."):
        engine.refine_node("s1", "instruction")
