from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import NodeMetadata, SummaryNode
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.exceptions import RefinementError


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

    # But returns empty generator for children (simulating missing/deleted children or mismatch)
    store.get_nodes.return_value = iter([])

    # This should raise "Node s1 has no accessible children. Cannot refine."
    with pytest.raises(RefinementError, match="has no accessible children"):
        engine.refine_node("s1", "instruction")
