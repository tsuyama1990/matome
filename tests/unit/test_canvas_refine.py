from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession


class TestMatomeCanvasRefine:

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        session = MagicMock(spec=InteractiveSession)
        session.param = MagicMock()
        session.param.breadcrumbs = []
        session.param.current_view_nodes = []
        session.param.selected_node = None
        session.param.is_processing = False
        return session

    @pytest.fixture
    def canvas(self, mock_session: MagicMock) -> MatomeCanvas:
        return MatomeCanvas(mock_session)

    def test_render_details_refinement_ui(self, canvas: MatomeCanvas, mock_session: MagicMock) -> None:
        """Test that refinement UI elements are created when a SummaryNode is selected."""
        node = SummaryNode(
            id="node_1",
            text="Summary Text",
            level=2,
            children_indices=[],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )

        # We need to capture the inner function bound by pn.bind
        def mock_bind(func: Any, *args: Any, **kwargs: Any) -> Any:
            return func  # Return the function directly so we can call it

        # Mock dependencies
        with patch("matome.ui.canvas.pn.bind", side_effect=mock_bind), \
             patch("matome.ui.canvas.pn.widgets.TextAreaInput") as MockTextArea, \
             patch("matome.ui.canvas.pn.widgets.Button") as MockButton, \
             patch("matome.ui.canvas.pn.indicators.LoadingSpinner") as MockSpinner, \
             patch("matome.ui.canvas.pn.Column"), \
             patch("matome.ui.canvas.pn.pane.Markdown"):

            # Execute: Get the render function
            render_func = canvas._render_details()

            # Execute: Call the render function with a node
            # This simulates Panel updating the view when selected_node changes
            render_func(node, False)

            # Verification (Red Phase: Expect Failure)
            # We expect these widgets to be instantiated
            MockTextArea.assert_called()
            MockButton.assert_called()
            MockSpinner.assert_called()

            # Verify structure
            # MockColumn should be called with children including TextArea and Button
            # We can inspect call_args but just knowing they were created is enough for now.

    def test_refine_button_callback(self, canvas: MatomeCanvas, mock_session: MagicMock) -> None:
        """Test that clicking the Refine button triggers the session action with correct parameters."""
        node = SummaryNode(
            id="node_1",
            text="Summary Text",
            level=2,
            children_indices=[],
            metadata=NodeMetadata(dikw_level=DIKWLevel.KNOWLEDGE)
        )

        # Mock pn.bind to simply return the function it wraps
        def mock_bind(func: Any, *args: Any, **kwargs: Any) -> Any:
            return func

        # Setup separate mocks for buttons
        mock_refine_button = MagicMock(name="RefineButton")
        mock_source_button = MagicMock(name="SourceButton")

        def button_side_effect(**kwargs: Any) -> MagicMock:
            if kwargs.get('name') == "Refine":
                return mock_refine_button
            if kwargs.get('name') == "Show Source":
                return mock_source_button
            return MagicMock()

        mock_textarea_instance = MagicMock()
        mock_textarea_instance.value = "New Instruction"

        with patch("matome.ui.canvas.pn.bind", side_effect=mock_bind), \
             patch("matome.ui.canvas.pn.widgets.TextAreaInput", return_value=mock_textarea_instance), \
             patch("matome.ui.canvas.pn.widgets.Button", side_effect=button_side_effect), \
             patch("matome.ui.canvas.pn.indicators.LoadingSpinner"), \
             patch("matome.ui.canvas.pn.Column"), \
             patch("matome.ui.canvas.pn.pane.Markdown"):

            render_func = canvas._render_details()
            render_func(node, False)

            # Verify button callback was registered
            mock_refine_button.on_click.assert_called()

            # Get the callback function
            callback = mock_refine_button.on_click.call_args[0][0]

            # Execute callback
            callback(None)  # Event object is ignored usually

            # Verify session method called with instruction
            mock_session.refine_current_node.assert_called_with("New Instruction")
