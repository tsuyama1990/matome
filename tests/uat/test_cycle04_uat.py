from unittest.mock import MagicMock

import pytest

from domain_models.data_schema import DIKWLevel, NodeMetadata
from domain_models.manifest import SummaryNode
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.ui.session import InteractiveSession


@pytest.fixture
def uat_engine() -> MagicMock:
    """Mock engine for UAT."""
    engine = MagicMock(spec=InteractiveRaptorEngine)

    # Setup some nodes
    wisdom_nodes = [
        SummaryNode(id="w1", text="Wisdom 1", level=3, children_indices=[], metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM))
    ]
    engine.get_nodes_by_level.return_value = wisdom_nodes
    engine.get_node.side_effect = lambda nid: wisdom_nodes[0] if nid == "w1" else None

    # Setup refinement
    def refine_side_effect(nid: str, instr: str) -> SummaryNode:
        return SummaryNode(
            id=nid,
            text="Refined Wisdom 1",
            level=3,
            children_indices=[],
            metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM, is_user_edited=True, refinement_history=[instr])
        )
    engine.refine_node.side_effect = refine_side_effect

    return engine

def test_cycle04_uat_flow(uat_engine: MagicMock) -> None:
    """
    Simulate the full UAT flow: Launch -> Select -> Refine.
    """
    # 1. Launch (Session Init)
    session = InteractiveSession(engine=uat_engine)

    # Verify initial state (Cycle 04-01)
    assert session.current_level == DIKWLevel.WISDOM
    assert len(session.available_nodes) == 1
    assert session.available_nodes[0].id == "w1"

    # 2. Node Selection (Cycle 04-02)
    # Simulate user selecting node from list (via View binding or ViewModel directly)
    # We'll use ViewModel directly as binding is tested in unit tests
    session.select_node("w1")

    assert session.selected_node is not None
    assert session.selected_node.id == "w1"
    assert "Selected node w1" in session.status_message

    # 3. Refinement (Cycle 04-03)
    instruction = "Make it shorter"
    session.refinement_instruction = instruction

    # Simulate button click
    session.submit_refinement()

    # Verify state after refinement
    assert session.is_refining is False
    assert session.refinement_instruction == ""
    assert "Refinement complete" in session.status_message
    assert session.selected_node.text == "Refined Wisdom 1"
    assert session.selected_node.metadata.is_user_edited is True

    # Verify available_nodes updated
    assert session.available_nodes[0].text == "Refined Wisdom 1"
