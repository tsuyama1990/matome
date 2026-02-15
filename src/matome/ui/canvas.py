import logging
from typing import Any

import panel as pn
from panel.viewable import Viewable

from domain_models.manifest import Chunk, SummaryNode
from domain_models.types import NodeID
from matome.ui.view_model import InteractiveSession

logger = logging.getLogger(__name__)

class MatomeCanvas:
    """
    The View component for Matome GUI.
    """
    def __init__(self, session: InteractiveSession) -> None:
        self.session = session
        self._template: pn.template.MaterialTemplate | None = None
        # Default format if not in config (though config usually has it, this is a UI-specific constant)
        # Assuming session.engine.config has level_format (added in recent refactor)
        # Ensure we use the configuration correctly without silent fallback
        self._level_format = session.engine.config.level_format

    def view(self) -> pn.template.MaterialTemplate:
        """Return the main template."""
        if self._template is None:
            self._template = pn.template.MaterialTemplate(  # type: ignore[no-untyped-call]
                title="Matome: Knowledge Installation",
                sidebar=[self._render_details()],
                main=[self._render_main_area()],
            )
            self._template.modal.append(self._render_source_viewer())
        return self._template

    def _render_source_viewer(self) -> Viewable:
        """Render the source chunks viewer modal content."""
        def _content(show: bool, chunks: list[Chunk]) -> Viewable:
            if not show:
                return pn.Column()

            close_btn = pn.widgets.Button(name="Close", button_type="light")  # type: ignore[no-untyped-call]

            def close(e: Any) -> None:
                self.session.show_source_chunks = False

            close_btn.on_click(close)

            chunk_views: list[Viewable] = []
            for chunk in chunks:
                chunk_views.append(
                    pn.Card(  # type: ignore[no-untyped-call]
                        pn.pane.Markdown(chunk.text),  # type: ignore[no-untyped-call]
                        title=f"Chunk {chunk.index}",
                        collapsed=False,
                        sizing_mode="stretch_width"
                    )
                )

            return pn.Column(
                pn.Row(pn.pane.Markdown("## Source Verification"), pn.Spacer(), close_btn),  # type: ignore[no-untyped-call]
                pn.Column(*chunk_views, scroll=True, height=600, sizing_mode="stretch_width"),
                sizing_mode="stretch_width"
            )

        return pn.bind(_content, self.session.param.show_source_chunks, self.session.param.source_chunks)  # type: ignore[no-any-return]

    def _render_main_area(self) -> pn.Column:
        """Render the main content area with breadcrumbs and pyramid view."""
        return pn.Column(
            self._render_breadcrumbs(),
            self._render_pyramid_view(),
            sizing_mode="stretch_width"
        )

    def _format_level_label(self, level: int, dikw_val: str) -> str:
        """Format the level label using configuration."""
        return self._level_format.format(level=level, dikw=dikw_val.upper())

    def _render_breadcrumbs(self) -> Viewable:
        """Render the breadcrumb navigation rail."""
        def _breadcrumbs(breadcrumbs: list[SummaryNode | Chunk]) -> pn.Row:
            try:
                items: list[Viewable] = []
                for i, node in enumerate(breadcrumbs):
                    if isinstance(node, SummaryNode):
                        label = self._format_level_label(node.level, node.metadata.dikw_level.value)
                        node_id = node.id
                    else:
                        label = f"Chunk {node.index}"
                        node_id = str(node.index)

                    btn = pn.widgets.Button(name=label, button_type="light", height=30)  # type: ignore[no-untyped-call]

                    # Use default argument to capture loop variable
                    def click_handler(e: Any, nid: str | int = node_id) -> None:
                        self._handle_selection(nid)

                    btn.on_click(click_handler)
                    items.append(btn)

                    if i < len(breadcrumbs) - 1:
                        items.append(pn.pane.Markdown(" > ", align="center"))  # type: ignore[no-untyped-call]

                return pn.Row(*items, sizing_mode="stretch_width")
            except Exception:
                logger.exception("Error rendering breadcrumbs")
                return pn.pane.Markdown("Error rendering breadcrumbs", style={"color": "red"})  # type: ignore[no-untyped-call]

        # We bind to the parameter itself
        return pn.bind(_breadcrumbs, self.session.param.breadcrumbs)  # type: ignore[no-any-return]

    def _render_pyramid_nodes(self, nodes: list[SummaryNode | Chunk]) -> Viewable:
        """Internal method to render pyramid nodes."""
        try:
            if not nodes:
                return pn.pane.Markdown("No child nodes to display.", sizing_mode="stretch_width")  # type: ignore[no-untyped-call]

            cards: list[Viewable] = []
            for node in nodes:
                if isinstance(node, SummaryNode):
                    title = f"{node.metadata.dikw_level.value.upper()}"
                    text_preview = node.text[:200] + "..." if len(node.text) > 200 else node.text
                    node_id = str(node.id)
                else:
                    title = f"Chunk {node.index}"
                    text_preview = node.text[:200] + "..." if len(node.text) > 200 else node.text
                    node_id = str(node.index)

                btn = pn.widgets.Button(name="Zoom In", button_type="primary")  # type: ignore[no-untyped-call]

                def click_handler(e: Any, nid: str | int = node_id) -> None:
                    self._handle_selection(nid)

                btn.on_click(click_handler)

                # Using a simple Card or Box
                container = pn.Card(  # type: ignore[no-untyped-call]
                    pn.pane.Markdown(text_preview),  # type: ignore[no-untyped-call]
                    btn,
                    title=title,
                    sizing_mode="stretch_width",
                    collapsed=False
                )
                cards.append(container)

            return pn.FlexBox(*cards, justify_content="center", sizing_mode="stretch_width")  # type: ignore[no-untyped-call]
        except Exception:
            logger.exception("Error rendering nodes")
            return pn.pane.Markdown("Error rendering nodes", style={"color": "red"})  # type: ignore[no-untyped-call]

    def _render_pyramid_view(self) -> Viewable:
        """Bind the pyramid view to the current view nodes."""
        return pn.bind(self._render_pyramid_nodes, self.session.param.current_view_nodes)  # type: ignore[no-any-return]

    def _handle_selection(self, node_id: NodeID) -> None:
        """Handle node selection with error handling."""
        try:
            self.session.select_node(node_id)
        except Exception as ex:
            logger.exception(f"Selection failed for node {node_id}")
            if pn.state.notifications:
                pn.state.notifications.error(f"Selection failed: {ex}")  # type: ignore[no-untyped-call]

    def _render_node_details(self, node: SummaryNode | Chunk | None, is_processing: bool) -> pn.Column:
        """Internal method to render details, extracted for testing."""
        try:
            if not node:
                return pn.Column(pn.pane.Markdown("Select a node to view details."))  # type: ignore[no-untyped-call]

            if isinstance(node, SummaryNode):
                title = f"Node: {node.id}"
                content = node.text
                meta = node.metadata
                meta_md = f"""
                **Level**: {node.level} ({meta.dikw_level.value})
                **Edited**: {meta.is_user_edited}
                **Refinements**: {len(meta.refinement_history)}
                """

                # Refinement UI
                instruction_input = pn.widgets.TextAreaInput(
                    name="Refine Node",
                    placeholder="Enter instruction (e.g., 'Simplify this', 'Translate to Japanese')...",
                    height=100,
                    disabled=is_processing,
                )

                refine_btn = pn.widgets.Button(
                    name="Refine",
                    button_type="primary",
                    disabled=is_processing,
                )  # type: ignore[no-untyped-call]

                def on_refine(event: Any) -> None:
                    if instruction_input.value:
                        self.session.refine_current_node(instruction_input.value)

                refine_btn.on_click(on_refine)

                source_btn = pn.widgets.Button(
                    name="Show Source",
                    button_type="default",
                    disabled=is_processing,
                )  # type: ignore[no-untyped-call]

                def on_show_source(event: Any) -> None:
                    self.session.load_source_chunks(node.id)

                source_btn.on_click(on_show_source)

                spinner = pn.indicators.LoadingSpinner(
                    value=is_processing,
                    width=25,
                    height=25,
                    align="center",
                )  # type: ignore[no-untyped-call]

                # Only show spinner if processing
                spinner.visible = is_processing

                refine_panel = pn.Column(
                    pn.pane.Markdown("### Actions"),  # type: ignore[no-untyped-call]
                    instruction_input,
                    pn.Row(refine_btn, source_btn, spinner),
                    sizing_mode="stretch_width",
                )

            else:
                title = f"Chunk {node.index}"
                content = node.text
                meta_md = f"""
                **Range**: {node.start_char_idx} - {node.end_char_idx}
                """
                refine_panel = pn.Column()  # Empty for chunks

            return pn.Column(
                pn.pane.Markdown(f"## {title}"),  # type: ignore[no-untyped-call]
                pn.pane.Markdown(meta_md),  # type: ignore[no-untyped-call]
                pn.pane.Markdown("### Content"),  # type: ignore[no-untyped-call]
                pn.pane.Markdown(content, sizing_mode="stretch_width"),  # type: ignore[no-untyped-call]
                refine_panel,
                sizing_mode="stretch_width"
            )
        except Exception:
            logger.exception("Error rendering details")
            return pn.Column(pn.pane.Markdown("Error rendering details", styles={"color": "red"}))  # type: ignore[no-untyped-call]

    def _render_details(self) -> Viewable:
        """Bind the details view to the selected node."""
        return pn.bind(self._render_node_details, self.session.param.selected_node, self.session.param.is_processing)  # type: ignore[no-any-return]
