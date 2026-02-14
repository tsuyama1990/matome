from unittest.mock import MagicMock

import panel as pn
import pytest

from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession


class TestCycle04UAT:
    """
    UAT for Cycle 04: Interactive Refinement.
    Verifies the end-to-end flow of refining a node via the GUI components.
    """

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        engine = MagicMock(spec=InteractiveRaptorEngine)
        engine.get_root_node.return_value = None
        engine.get_node.return_value = None
        engine.get_children.return_value = []
        return engine

    @pytest.fixture
    def session(self, mock_engine: MagicMock) -> InteractiveSession:
        return InteractiveSession(engine=mock_engine)

    @pytest.fixture
    def canvas(self, session: InteractiveSession) -> MatomeCanvas:
        return MatomeCanvas(session)

    def test_refinement_flow(self, canvas: MatomeCanvas, session: InteractiveSession, mock_engine: MagicMock) -> None:
        """
        Scenario: User selects a node, enters instruction, clicks Refine.
        Expected: Engine is called, Node is updated, UI reflects changes.
        """
        # 1. Setup Initial State
        original_node = SummaryNode(
            id="node_1",
            text="Original Text",
            level=2,
            children_indices=[],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )
        refined_node = SummaryNode(
            id="node_1", # ID stays same
            text="Refined Text",
            level=2,
            children_indices=[],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE, is_user_edited=True, refinement_history=["Simplify"])
        )

        # Mock engine behavior
        # When get_node is called, return original_node initially
        # But after refinement, selected_node is updated in session.
        # Note: session.select_node calls engine.get_node.
        mock_engine.get_node.side_effect = lambda nid: original_node if nid == "node_1" else None
        mock_engine.refine_node.return_value = refined_node

        # 2. Simulate User Selection
        session.select_node("node_1")
        assert session.selected_node == original_node

        # 3. Simulate UI Interaction
        # Access the bound function from _render_details
        render_func = canvas._render_details()

        # Invoke it to get the Column
        # Since it is bound to session params, calling it without args should use current param values
        ui_column = render_func()

        # Inspect UI Column
        # Structure check:
        # We look for the Refinement Panel.
        # It should be the last element (index 4)
        assert len(ui_column) >= 5
        refinement_panel = ui_column[4]
        assert isinstance(refinement_panel, pn.Column)

        # Refinement Panel: [Markdown, TextArea, Row(Button, Spinner)]
        # Index 1 should be TextArea
        textarea = refinement_panel[1]
        assert isinstance(textarea, pn.widgets.TextAreaInput)

        # Index 2 should be Row
        button_row = refinement_panel[2]
        assert isinstance(button_row, pn.Row)

        button = button_row[0]
        assert isinstance(button, pn.widgets.Button)
        assert button.name == "Refine"

        # 4. Perform Action
        textarea.value = "Simplify"

        # Simulate button click
        # We trigger the click event by incrementing clicks
        button.clicks += 1

        # 5. Verify Outcome
        mock_engine.refine_node.assert_called_with("node_1", "Simplify")
        assert session.selected_node == refined_node
        assert session.selected_node.text == "Refined Text"
        assert session.is_processing is False

        # Verify UI update (optional, but good to check)
        # Re-rendering should show new text
        ui_column_updated = render_func()
        content_markdown = ui_column_updated[3]
        assert "Refined Text" in content_markdown.object

