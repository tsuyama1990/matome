import typing

import param

from domain_models.data_schema import DIKWLevel
from domain_models.manifest import Chunk, SummaryNode
from matome.engines.interactive_raptor import InteractiveRaptorEngine


class InteractiveSession(param.Parameterized):  # type: ignore[misc]
    """
    ViewModel for the Matome Interactive GUI.
    Manages state and business logic, mediating between View and Engine.
    """

    # State
    # Support Chunk for read-only selection
    selected_node = param.ClassSelector(
        class_=(SummaryNode, Chunk), allow_None=True, doc="Currently selected node."
    )
    current_level = param.Selector(
        objects=list(DIKWLevel), default=DIKWLevel.WISDOM, doc="Current abstraction level."
    )
    is_refining = param.Boolean(
        default=False, doc="Whether a refinement operation is in progress."
    )
    refinement_instruction = param.String(
        default="", doc="User instruction for refinement."
    )
    status_message = param.String(
        default="Ready", doc="Status message to display to the user."
    )

    # Navigation State (Zooming)
    view_context = param.ClassSelector(
        class_=SummaryNode, allow_None=True, doc="Current parent node being viewed."
    )
    breadcrumbs = param.List(
        default=[], item_type=SummaryNode, doc="Navigation stack."
    )

    # Data source for the list view
    available_nodes = param.List(
        default=[], doc="List of nodes available at the current level."
    )

    def __init__(
        self, engine: InteractiveRaptorEngine, **params: typing.Any
    ) -> None:
        super().__init__(**params)
        self.engine = engine
        self._update_available_nodes()

    @param.depends("current_level", "view_context", watch=True)
    def _update_available_nodes(self) -> None:
        """Fetch nodes for the selected level or context."""
        self.status_message = "Loading nodes..."
        try:
            nodes: list[SummaryNode | Chunk]
            if self.view_context:
                # Zoomed in: Fetch children of current context
                nodes = self.engine.get_children(self.view_context.id)
                self.status_message = f"Loaded {len(nodes)} children."
            else:
                # Root view: Fetch by level
                # get_nodes_by_level returns list[SummaryNode]
                nodes = self.engine.get_nodes_by_level(self.current_level)
                self.status_message = f"Loaded {len(nodes)} {self.current_level} nodes."

            self.available_nodes = nodes
            self.selected_node = None  # Clear selection on view change

        except Exception as e:
            self.status_message = f"Error loading nodes: {e}"

    def select_node(self, node_id: str | int) -> None:
        """Select a node by ID."""
        try:
            # Look in available_nodes to avoid DB hit and ensure it's in current view
            found = None
            node_id_str = str(node_id)

            for n in self.available_nodes:
                if isinstance(n, SummaryNode):
                    if n.id == node_id_str:
                        found = n
                        break
                elif isinstance(n, Chunk):
                    if str(n.index) == node_id_str:
                        found = n
                        break

            if found:
                self.selected_node = found
                self.status_message = f"Selected node {node_id}"
            else:
                # Fallback to engine
                node = self.engine.get_node(node_id_str)
                if node:
                    self.selected_node = node
                    self.status_message = f"Selected node {node_id}"
                else:
                     self.status_message = f"Node {node_id} not found."

        except Exception as e:
            self.status_message = f"Error selecting node: {e}"

    def submit_refinement(self) -> None:
        """Submit the refinement instruction for the selected node."""
        if not self.selected_node:
            self.status_message = "No node selected for refinement."
            return

        if isinstance(self.selected_node, Chunk):
            self.status_message = "Cannot refine a raw Chunk. Only summaries can be refined."
            return

        if not self.refinement_instruction.strip():
            self.status_message = "Please enter instructions for refinement."
            return

        self.is_refining = True
        self.status_message = "Refining node... (this may take a moment)"

        try:
            # We must use self.selected_node.id because self.selected_node is a copy/object
            new_node = self.engine.refine_node(
                self.selected_node.id, self.refinement_instruction
            )

            # Update selection to the new node
            self.selected_node = new_node

            # Clear instruction
            self.refinement_instruction = ""
            self.status_message = "Refinement complete. Node updated."

            # Refresh list to show updated content if needed
            new_list = list(self.available_nodes)
            for i, n in enumerate(new_list):
                 # Check ID match safely
                 nid = getattr(n, 'id', None)
                 if nid == new_node.id:
                     new_list[i] = new_node
                     break
            self.available_nodes = new_list

        except Exception as e:
            self.status_message = f"Refinement failed: {e}"
        finally:
            self.is_refining = False

    def zoom_in(self, node: SummaryNode) -> None:
        """Zoom into a node to see its children."""
        if not node.children_indices:
             self.status_message = "Cannot zoom into a leaf node."
             return

        # Determine next level
        next_level = self._get_next_level(node.metadata.dikw_level)
        if not next_level:
            self.status_message = "Cannot zoom further (unknown level)."
            return

        # Update state
        self.breadcrumbs = [*self.breadcrumbs, node]
        self.view_context = node
        self.current_level = next_level

    def zoom_out(self) -> None:
        """Go back one step in breadcrumbs."""
        if not self.breadcrumbs:
            return

        # Pop last breadcrumb
        popped = self.breadcrumbs[-1]
        new_breadcrumbs = self.breadcrumbs[:-1]
        self.breadcrumbs = new_breadcrumbs

        if new_breadcrumbs:
            # Go back to parent of popped
            self.view_context = new_breadcrumbs[-1]
            self.current_level = self._get_next_level(self.view_context.metadata.dikw_level) or DIKWLevel.WISDOM
        else:
            # Back to Root
            self.view_context = None
            self.current_level = DIKWLevel.WISDOM

    def jump_to(self, node: SummaryNode) -> None:
        """Jump to a specific node in the breadcrumb path."""
        try:
            idx = self.breadcrumbs.index(node)
        except ValueError:
            # try finding by ID
            idx = -1
            for i, b in enumerate(self.breadcrumbs):
                if b.id == node.id:
                    idx = i
                    break
            if idx == -1:
                return

        self.breadcrumbs = self.breadcrumbs[:idx+1]
        self.view_context = node
        self.current_level = self._get_next_level(node.metadata.dikw_level) or DIKWLevel.WISDOM

    def get_source(self, node: SummaryNode) -> list[Chunk]:
        """Get source chunks for a node."""
        return self.engine.get_source_chunks(node.id)

    def _get_next_level(self, current: DIKWLevel) -> DIKWLevel | None:
        if current == DIKWLevel.WISDOM: return DIKWLevel.KNOWLEDGE
        if current == DIKWLevel.KNOWLEDGE: return DIKWLevel.INFORMATION
        if current == DIKWLevel.INFORMATION: return DIKWLevel.DATA
        return None
