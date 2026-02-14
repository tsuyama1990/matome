from typing import Any

import panel as pn

from domain_models.manifest import Chunk, SummaryNode
from matome.ui.view_model import InteractiveSession


class MatomeCanvas:
    """
    The View component for Matome GUI.
    """
    def __init__(self, session: InteractiveSession) -> None:
        self.session = session
        self._template: pn.template.MaterialTemplate | None = None

    def view(self) -> pn.template.MaterialTemplate:
        """Return the main template."""
        if self._template is None:
            self._template = pn.template.MaterialTemplate(  # type: ignore[no-untyped-call]
                title="Matome: Knowledge Installation",
                sidebar=[self._render_details()],
                main=[self._render_main_area()],
            )
        return self._template

    def _render_main_area(self) -> pn.Column:
        return pn.Column(
            self._render_breadcrumbs,
            self._render_pyramid_view,
            sizing_mode="stretch_width"
        )

    def _render_breadcrumbs(self) -> Any:
        def _breadcrumbs(breadcrumbs: list[SummaryNode | Chunk]) -> pn.Row:
            try:
                items = []
                for i, node in enumerate(breadcrumbs):
                    if isinstance(node, SummaryNode):
                        label = f"L{node.level}: {node.metadata.dikw_level.value.upper()}"
                        node_id = node.id
                    else:
                        label = f"Chunk {node.index}"
                        node_id = str(node.index)

                    btn = pn.widgets.Button(name=label, button_type="light", height=30)  # type: ignore[no-untyped-call]

                    # Use default argument to capture loop variable
                    def click_handler(e: Any, nid: str | int = node_id) -> None:
                        try:
                            self.session.select_node(nid)
                        except Exception as ex:
                            if pn.state.notifications:
                                pn.state.notifications.error(f"Navigation failed: {ex}")  # type: ignore[no-untyped-call]

                    btn.on_click(click_handler)
                    items.append(btn)

                    if i < len(breadcrumbs) - 1:
                        items.append(pn.pane.Markdown(" > ", align="center"))  # type: ignore[no-untyped-call]

                return pn.Row(*items, sizing_mode="stretch_width")
            except Exception as e:
                return pn.pane.Markdown(f"Error rendering breadcrumbs: {e}", style={"color": "red"})  # type: ignore[no-untyped-call]

        # We bind to the parameter itself
        return pn.bind(_breadcrumbs, self.session.param.breadcrumbs)

    def _render_pyramid_view(self) -> Any:
        def _view_nodes(nodes: list[SummaryNode | Chunk]) -> Any:
            try:
                if not nodes:
                    # If no children, maybe we are at leaf or root just loaded?
                    # If root is loaded, it should be in breadcrumbs and visible?
                    # Actually, current_view_nodes are children of selected node.
                    # If selected node is leaf, no children.
                    return pn.pane.Markdown("No child nodes to display.", sizing_mode="stretch_width")  # type: ignore[no-untyped-call]

                cards = []
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
                        try:
                            self.session.select_node(nid)
                        except Exception as ex:
                            if pn.state.notifications:
                                pn.state.notifications.error(f"Selection failed: {ex}")  # type: ignore[no-untyped-call]

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
            except Exception as e:
                return pn.pane.Markdown(f"Error rendering nodes: {e}", style={"color": "red"})  # type: ignore[no-untyped-call]

        return pn.bind(_view_nodes, self.session.param.current_view_nodes)

    def _render_details(self) -> Any:
        def _details(node: SummaryNode | Chunk | None) -> pn.Column:
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
                else:
                    title = f"Chunk {node.index}"
                    content = node.text
                    meta_md = f"""
                    **Range**: {node.start_char_idx} - {node.end_char_idx}
                    """

                return pn.Column(
                    pn.pane.Markdown(f"## {title}"),  # type: ignore[no-untyped-call]
                    pn.pane.Markdown(meta_md),  # type: ignore[no-untyped-call]
                    pn.pane.Markdown("### Content"),  # type: ignore[no-untyped-call]
                    pn.pane.Markdown(content, sizing_mode="stretch_width"),  # type: ignore[no-untyped-call]
                    sizing_mode="stretch_width"
                )
            except Exception as e:
                return pn.Column(pn.pane.Markdown(f"Error rendering details: {e}", style={"color": "red"}))  # type: ignore[no-untyped-call]

        return pn.bind(_details, self.session.param.selected_node)
