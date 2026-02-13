from unittest.mock import MagicMock

import pytest

from domain_models.data_schema import DIKWLevel, NodeMetadata
from domain_models.manifest import Chunk, SummaryNode
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.ui.session import InteractiveSession


@pytest.fixture
def uat_engine() -> MagicMock:
    """
    Create a mock engine with a predefined tree structure for UAT.
    Tree:
    Wisdom (W1)
      -> Knowledge (K1)
           -> Information (I1)
                -> Chunk (C1)
    """
    engine = MagicMock(spec=InteractiveRaptorEngine)

    # Data
    c1 = Chunk(index=1, text="Chunk Text", start_char_idx=0, end_char_idx=10)

    i1 = SummaryNode(
        id="I1", text="Info", level=1, children_indices=[1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )

    k1 = SummaryNode(
        id="K1", text="Knowledge", level=2, children_indices=["I1"],
        metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
    )

    w1 = SummaryNode(
        id="W1", text="Wisdom", level=3, children_indices=["K1"],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM)
    )

    _configure_get_nodes(engine, w1, k1, i1)
    _configure_get_node(engine, w1, k1, i1, c1)
    _configure_get_children(engine, w1, k1, i1, c1)

    def get_source_chunks(nid: str) -> list[Chunk]:
        return [c1]

    engine.get_source_chunks.side_effect = get_source_chunks

    return engine


def _configure_get_nodes(engine: MagicMock, w1: SummaryNode, k1: SummaryNode, i1: SummaryNode) -> None:
    def get_nodes_by_level(level: str) -> list[SummaryNode]:
        if level == DIKWLevel.WISDOM:
            return [w1]
        if level == DIKWLevel.KNOWLEDGE:
            return [k1]
        if level == DIKWLevel.INFORMATION:
            return [i1]
        return []
    engine.get_nodes_by_level.side_effect = get_nodes_by_level


def _configure_get_node(engine: MagicMock, w1: SummaryNode, k1: SummaryNode, i1: SummaryNode, c1: Chunk) -> None:
    def get_node(nid: str) -> SummaryNode | Chunk | None:
        mapping: dict[str, SummaryNode | Chunk] = {"W1": w1, "K1": k1, "I1": i1, "1": c1}
        return mapping.get(nid)
    engine.get_node.side_effect = get_node


def _configure_get_children(engine: MagicMock, w1: SummaryNode, k1: SummaryNode, i1: SummaryNode, c1: Chunk) -> None:
    def get_children(nid: str) -> list[SummaryNode | Chunk]:
        if nid == "W1":
            return [k1]
        if nid == "K1":
            return [i1]
        if nid == "I1":
            return [c1]
        return []
    engine.get_children.side_effect = get_children


def test_cycle05_user_journey(uat_engine: MagicMock) -> None:
    """
    Simulates the full user journey:
    1. Load App (Wisdom level)
    2. Zoom In (Wisdom -> Knowledge)
    3. Zoom In (Knowledge -> Information)
    4. View Source (Check Chunks)
    5. Refine Node
    """

    # 1. Load App
    session = InteractiveSession(engine=uat_engine)

    # Verify initial state
    assert session.current_level == DIKWLevel.WISDOM
    assert len(session.available_nodes) == 1
    assert isinstance(session.available_nodes[0], SummaryNode)
    assert session.available_nodes[0].id == "W1"

    # 2. Zoom In on Wisdom Node
    w1 = session.available_nodes[0]
    assert isinstance(w1, SummaryNode)
    session.zoom_in(w1)

    # Verify Zoom to Knowledge
    assert session.current_level == DIKWLevel.KNOWLEDGE  # type: ignore[comparison-overlap]
    assert session.view_context and session.view_context.id == "W1"
    assert len(session.breadcrumbs) == 1
    assert len(session.available_nodes) == 1
    assert isinstance(session.available_nodes[0], SummaryNode)
    assert session.available_nodes[0].id == "K1"

    # 3. Zoom In on Knowledge Node
    k1 = session.available_nodes[0]
    assert isinstance(k1, SummaryNode)
    session.zoom_in(k1)

    # Verify Zoom to Information
    assert session.current_level == DIKWLevel.INFORMATION
    assert session.view_context and session.view_context.id == "K1"
    assert len(session.breadcrumbs) == 2
    assert isinstance(session.available_nodes[0], SummaryNode)
    assert session.available_nodes[0].id == "I1"

    # 4. View Source
    i1 = session.available_nodes[0]
    sources = session.get_source(i1)
    assert len(sources) == 1
    assert sources[0].text == "Chunk Text"

    # 5. Refine Node
    session.select_node("I1")
    session.refinement_instruction = "Clarify this"

    # Mock refinement result
    refined_i1 = SummaryNode(
        id="I1", text="Clarified Info", level=1, children_indices=[1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION, is_user_edited=True)
    )
    uat_engine.refine_node.return_value = refined_i1

    session.submit_refinement()

    # Verify Refinement
    assert session.selected_node.text == "Clarified Info"
    assert session.available_nodes[0].text == "Clarified Info"
    uat_engine.refine_node.assert_called_with("I1", "Clarify this")
