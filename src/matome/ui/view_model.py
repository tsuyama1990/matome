import itertools
from typing import Any

import param

from domain_models.manifest import Chunk, SummaryNode
from domain_models.types import NodeID
from matome.engines.interactive_raptor import InteractiveRaptorEngine


class InteractiveSession(param.Parameterized):  # type: ignore[misc]
    """
    ViewModel for the Matome Interactive GUI.
    Manages the state of navigation (root, selection, breadcrumbs).
    """
    engine = param.ClassSelector(class_=InteractiveRaptorEngine, precedence=-1)

    root_node = param.ClassSelector(class_=SummaryNode, allow_None=True)
    selected_node = param.ClassSelector(class_=(SummaryNode, Chunk), allow_None=True)

    # Use item_type to hint the contents of the list, although param validation might be strict
    breadcrumbs = param.List(default=[], item_type=(SummaryNode, Chunk))
    current_view_nodes = param.List(default=[], item_type=(SummaryNode, Chunk))

    # Traceability
    source_chunks = param.List(default=[], item_type=Chunk)
    show_source_chunks = param.Boolean(default=False)

    is_processing = param.Boolean(default=False)

    def __init__(self, engine: InteractiveRaptorEngine, **params: Any) -> None:
        super().__init__(engine=engine, **params)

    def load_tree(self) -> None:
        """Initialize the session by loading the root node."""
        root = self.engine.get_root_node()
        if root:
            self.root_node = root
            # When loading tree, we select the root
            self.select_node(root.id)
        else:
            # If no root found (empty db), clear state
            self.root_node = None
            self.selected_node = None
            self.breadcrumbs = []
            self.current_view_nodes = []

    def select_node(self, node_id: NodeID) -> None:
        """Select a node and update view state."""
        try:
            node = self.engine.get_node(node_id)
        except Exception:
            # Handle store errors gracefully
            return

        if not node:
            return

        self.selected_node = node

        # Update breadcrumbs
        new_breadcrumbs = []
        found = False

        node_id_str = str(node.id) if isinstance(node, SummaryNode) else str(node.index)

        for crumb in self.breadcrumbs:
            new_breadcrumbs.append(crumb)
            crumb_id = str(crumb.id) if isinstance(crumb, SummaryNode) else str(crumb.index)

            if crumb_id == node_id_str:
                found = True
                break

        if found:
            self.breadcrumbs = new_breadcrumbs
        elif not self.breadcrumbs:
            self.breadcrumbs = [node]
        else:
            self.breadcrumbs.append(node)

        # Update current view nodes (children of selected node)
        if isinstance(node, SummaryNode):
            # get_children returns an Iterator.
            # Limit the number of children displayed to avoid UI overload.
            limit = self.engine.config.ui_max_children
            # Use islice to safely limit memory usage when materializing for UI
            self.current_view_nodes = list(itertools.islice(self.engine.get_children(node), limit))
        else:
            self.current_view_nodes = []

    def refine_current_node(self, instruction: str) -> None:
        """
        Refine the currently selected node using the given instruction.
        """
        if not self.selected_node:
            return

        if not isinstance(self.selected_node, SummaryNode):
            msg = "Only SummaryNodes can be refined."
            raise TypeError(msg)

        self.is_processing = True
        try:
            updated_node = self.engine.refine_node(self.selected_node.id, instruction)
            self.selected_node = updated_node

            # Update breadcrumbs to reflect the new node instance
            # This ensures navigation history remains valid with the updated content
            new_breadcrumbs = []
            for crumb in self.breadcrumbs:
                if isinstance(crumb, SummaryNode) and crumb.id == updated_node.id:
                    new_breadcrumbs.append(updated_node)
                else:
                    new_breadcrumbs.append(crumb)
            self.breadcrumbs = new_breadcrumbs

        finally:
            self.is_processing = False

    def load_source_chunks(self, node_id: NodeID) -> None:
        """
        Load the source chunks for the given node and display them.
        """
        self.is_processing = True
        try:
            limit = self.engine.config.ui_max_source_chunks
            # Materialize iterator up to limit
            chunks_iter = self.engine.get_source_chunks(node_id, limit=limit)
            self.source_chunks = list(chunks_iter)
            self.show_source_chunks = True
        except Exception:
            # In a real app we might want to show a notification
            self.source_chunks = []
            self.show_source_chunks = False
            raise
        finally:
            self.is_processing = False
