import panel as pn
import param

from domain_models.manifest import SummaryNode
from matome.ui.session import InteractiveSession

# Initialize panel extension
pn.extension("material")


class MatomeCanvas(param.Parameterized):
    """
    The View component for the Matome GUI.
    Defines the layout and binds to the InteractiveSession ViewModel.
    """

    session = param.ClassSelector(class_=InteractiveSession, allow_None=False)

    def __init__(self, **params) -> None:
        super().__init__(**params)
        self._create_components()

    def _create_components(self) -> None:
        """Initialize UI components."""

        # Sidebar: Level Selector
        self.level_selector = pn.widgets.Select.from_param(
            self.session.param.current_level,
            name="DIKW Level",
            sizing_mode="stretch_width",
        )

        # Sidebar: Node List
        self.node_list = pn.bind(
            self._render_node_list, self.session.param.available_nodes
        )

        # Main Area: Detail View
        self.detail_view = pn.bind(
            self._render_detail_view, self.session.param.selected_node
        )

        # Main Area: Refinement Control
        self.refinement_input = pn.widgets.TextAreaInput.from_param(
            self.session.param.refinement_instruction,
            name="Refinement Instruction",
            placeholder="Enter instructions to refine this node...",
            height=100,
            sizing_mode="stretch_width",
        )

        self.submit_button = pn.widgets.Button(
            name="Refine Node", button_type="primary"
        )
        self.submit_button.on_click(lambda event: self.session.submit_refinement())

        # Bind button disabled state to is_refining and selection
        def update_button_state(is_refining: bool, selected_node: SummaryNode | None) -> None:
            self.submit_button.disabled = is_refining or (selected_node is None)
            self.submit_button.loading = is_refining

        pn.bind(
            update_button_state,
            self.session.param.is_refining,
            self.session.param.selected_node,
            watch=True,
        )

        # Status Bar
        self.status_bar = pn.widgets.StaticText.from_param(
            self.session.param.status_message, name="Status"
        )

    def _render_node_list(self, nodes: list[SummaryNode]) -> pn.viewable.Viewable:
        """Render the list of available nodes."""
        if not nodes:
            return pn.pane.Markdown("*No nodes available at this level.*")

        # Use a Select widget mapping labels to IDs
        options = {f"{n.id}: {n.text[:30]}...": n.id for n in nodes}

        selector = pn.widgets.Select(
            name="Select Node",
            options=options,
            size=15,  # show multiple items
            sizing_mode="stretch_width",
        )

        # When value changes, call session.select_node
        def on_change(event) -> None:
            if event.new:
                self.session.select_node(event.new)

        selector.param.watch(on_change, "value")
        return selector

    def _render_detail_view(self, node: SummaryNode | None) -> pn.viewable.Viewable:
        """Render the details of the selected node."""
        if node is None:
            return pn.pane.Markdown(
                "### No Node Selected\nPlease select a node from the sidebar."
            )

        # Construct detail view
        return pn.Column(
            pn.pane.Markdown(f"## Node: {node.id}"),
            pn.pane.Markdown(
                f"**Level**: {node.level} | **DIKW**: {node.metadata.dikw_level}"
            ),
            pn.pane.Markdown("### Content"),
            pn.pane.Markdown(
                node.text,
                style={
                    "background-color": "#f0f0f0",
                    "padding": "10px",
                    "border-radius": "5px",
                },
            ),
            pn.pane.Markdown("### Refinement History"),
            pn.pane.JSON(node.metadata.refinement_history, depth=1),
            sizing_mode="stretch_width",
        )

    @property
    def sidebar(self) -> pn.Column:
        return pn.Column(
            "## Navigation",
            self.level_selector,
            self.node_list,
            sizing_mode="stretch_width",
        )

    @property
    def main_area(self) -> pn.Column:
        return pn.Column(
            self.detail_view,
            pn.layout.Divider(),
            "### Refinement",
            self.refinement_input,
            self.submit_button,
            self.status_bar,
            sizing_mode="stretch_width",
        )

    @property
    def layout(self) -> pn.template.BaseTemplate:
        """Compose the final layout."""
        template = pn.template.MaterialTemplate(
            title="Matome 2.0: Knowledge Installation System",
            sidebar=[self.sidebar],
            main=[self.main_area],
        )
        return template
