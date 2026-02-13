from typing import Any

import panel as pn
import param

from domain_models.manifest import Chunk, SummaryNode
from matome.ui.session import InteractiveSession

# Initialize panel extension
pn.extension("material")


class MatomeCanvas(param.Parameterized):  # type: ignore[misc]
    """
    The View component for the Matome GUI.
    Defines the layout and binds to the InteractiveSession ViewModel.
    """

    session = param.ClassSelector(class_=InteractiveSession, allow_None=False)

    def __init__(self, **params: Any) -> None:
        super().__init__(**params)
        self._template: pn.template.MaterialTemplate | None = None
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

        # Main Area: Breadcrumbs
        self.breadcrumbs_view = pn.bind(
            self._render_breadcrumbs, self.session.param.breadcrumbs
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
        def update_button_state(
            is_refining: bool, selected_node: SummaryNode | Chunk | None
        ) -> None:
            # Cannot refine chunks
            is_chunk = isinstance(selected_node, Chunk)
            self.submit_button.disabled = is_refining or (selected_node is None) or is_chunk
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

    def _render_node_list(self, nodes: list[SummaryNode | Chunk]) -> pn.viewable.Viewable:
        """Render the list of available nodes."""
        if not nodes:
            return pn.pane.Markdown(
                "*No nodes available at this level.*"
            )

        # Use a Select widget mapping labels to IDs
        options = {}
        for n in nodes:
            # Handle both SummaryNode (id) and Chunk (index)
            if isinstance(n, SummaryNode):
                nid = n.id
                text = n.text
            elif isinstance(n, Chunk):
                nid = str(n.index)
                text = n.text
            else:
                continue

            label = f"{nid}: {text[:30]}..."
            options[label] = nid

        selector = pn.widgets.Select(
            name="Select Node",
            options=options,
            size=15,  # show multiple items
            sizing_mode="stretch_width",
        )

        # When value changes, call session.select_node
        def on_change(event: Any) -> None:
            if event.new:
                self.session.select_node(event.new)

        selector.param.watch(on_change, "value")
        return selector

    def _render_breadcrumbs(self, breadcrumbs: list[SummaryNode]) -> pn.viewable.Viewable:
        """Render navigation breadcrumbs."""
        buttons = []

        # Home button
        def go_home(event: Any) -> None:
             self.session.breadcrumbs = []
             self.session.view_context = None
             self.session.current_level = self.session.current_level.__class__.WISDOM

        home_btn = pn.widgets.Button(name="Home", button_type="light", width=80)
        home_btn.on_click(go_home)
        buttons.append(home_btn)

        for node in breadcrumbs:
            buttons.append(pn.pane.Markdown(" > ", align="center"))

            # Use level title or truncated text
            label = f"{node.metadata.dikw_level.title()}: {node.text[:10]}..."
            btn = pn.widgets.Button(name=label, button_type="light", height=30)

            # Closure capture
            def jump(event: Any, n: SummaryNode = node) -> None:
                self.session.jump_to(n)

            btn.on_click(jump)
            buttons.append(btn)

        return pn.Row(*buttons, sizing_mode="stretch_width")

    def _render_detail_view(self, node: SummaryNode | Chunk | None) -> pn.viewable.Viewable:
        """Render the details of the selected node."""
        if node is None:
            return pn.pane.Markdown(
                "### No Node Selected\nPlease select a node from the sidebar."
            )

        if isinstance(node, Chunk):
            # Render Chunk View
            return pn.Column(
                pn.pane.Markdown(f"## Chunk: {node.index}"),
                pn.pane.Markdown("**Level**: DATA (Read-Only)"),
                pn.pane.Markdown("### Content"),
                pn.pane.Markdown(
                    node.text,
                    style={
                        "background-color": "#f0f0f0",
                        "padding": "10px",
                        "border-radius": "5px",
                    },
                ),
                sizing_mode="stretch_width",
            )

        # Render SummaryNode View
        # Action Buttons
        buttons = []

        # Zoom In Button
        if isinstance(node, SummaryNode) and node.children_indices:
             zoom_btn = pn.widgets.Button(name="Zoom In", button_type="primary")
             zoom_btn.on_click(lambda e: self.session.zoom_in(node))
             buttons.append(zoom_btn)

        # View Source Button
        source_btn = pn.widgets.Button(name="View Source", button_type="default")
        source_btn.on_click(lambda e: self._show_source_modal(node))
        buttons.append(source_btn)

        # Construct detail view
        return pn.Column(
            pn.pane.Markdown(f"## Node: {node.id}"),
            pn.pane.Markdown(
                f"**Level**: {getattr(node, 'level', 'N/A')} | **DIKW**: {getattr(node.metadata, 'dikw_level', 'N/A') if hasattr(node, 'metadata') else 'DATA'}"
            ),
            pn.Row(*buttons),
            pn.pane.Markdown("### Content"),
            pn.pane.Markdown(
                node.text,
                style={
                    "background-color": "#f0f0f0",
                    "padding": "10px",
                    "border-radius": "5px",
                },
            ),
            # Only show refinement history for SummaryNodes
            pn.pane.Markdown("### Refinement History") if isinstance(node, SummaryNode) else None,
            pn.pane.JSON(
                node.metadata.refinement_history, depth=1
            ) if isinstance(node, SummaryNode) else None,
            sizing_mode="stretch_width",
        )

    def _show_source_modal(self, node: SummaryNode) -> None:
        """Show source chunks in a modal."""
        if not self._template:
            return

        # Fetch chunks (this might be slow, so ideally async, but Panel handles callbacks)
        self.session.status_message = "Fetching source chunks..."
        try:
            chunks = self.session.get_source(node)
            self.session.status_message = f"Found {len(chunks)} source chunks."
        except Exception as e:
            self.session.status_message = f"Error fetching source: {e}"
            return

        content = []
        for chunk in chunks:
            content.append(f"**Chunk {chunk.index}**")
            content.append(f"{chunk.text}")
            content.append("---")

        modal_content = pn.Column(
            "## Source Chunks",
            pn.pane.Markdown("\n".join(content), height=400, style={"overflow-y": "scroll"}),
            sizing_mode="stretch_width"
        )

        self._template.modal.clear()
        self._template.modal.append(modal_content)
        self._template.open_modal()

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
            self.breadcrumbs_view,
            pn.layout.Divider(),
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
        if self._template is None:
            self._template = pn.template.MaterialTemplate(
                title="Matome 2.0: Knowledge Installation System",
                sidebar=[self.sidebar],
                main=[self.main_area],
            )
        return self._template
