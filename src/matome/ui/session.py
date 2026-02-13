import param
from domain_models.data_schema import DIKWLevel
from domain_models.manifest import SummaryNode
from matome.engines.interactive_raptor import InteractiveRaptorEngine


class InteractiveSession(param.Parameterized):
    """
    ViewModel for the Matome Interactive GUI.
    Manages state and business logic, mediating between View and Engine.
    """

    # State
    selected_node = param.ClassSelector(
        class_=SummaryNode, allow_None=True, doc="Currently selected node."
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

    # Data source for the list view
    available_nodes = param.List(
        default=[], item_type=SummaryNode, doc="List of nodes available at the current level."
    )

    def __init__(self, engine: InteractiveRaptorEngine, **params) -> None:
        super().__init__(**params)
        self.engine = engine
        self._update_available_nodes()

    @param.depends("current_level", watch=True)
    def _update_available_nodes(self) -> None:
        """Fetch nodes for the selected level."""
        self.status_message = f"Loading {self.current_level} nodes..."
        try:
            nodes = self.engine.get_nodes_by_level(self.current_level)
            self.available_nodes = nodes
            self.selected_node = None  # Clear selection on level switch
            self.status_message = f"Loaded {len(nodes)} {self.current_level} nodes."
        except Exception as e:
            self.status_message = f"Error loading nodes: {e}"

    def select_node(self, node_id: str) -> None:
        """Select a node by ID."""
        try:
            node = self.engine.get_node(node_id)
            if isinstance(node, SummaryNode):
                self.selected_node = node
                self.status_message = f"Selected node {node_id}"
            else:
                self.status_message = (
                    f"Node {node_id} is not a SummaryNode (it might be a raw Chunk)."
                )
        except Exception as e:
            self.status_message = f"Error selecting node: {e}"

    def submit_refinement(self) -> None:
        """Submit the refinement instruction for the selected node."""
        if not self.selected_node:
            self.status_message = "No node selected for refinement."
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
            idx = -1
            for i, n in enumerate(self.available_nodes):
                if n.id == new_node.id:
                    idx = i
                    break
            if idx != -1:
                # Trigger update by creating a new list copy
                new_list = list(self.available_nodes)
                new_list[idx] = new_node
                self.available_nodes = new_list

        except Exception as e:
            self.status_message = f"Refinement failed: {e}"
        finally:
            self.is_refining = False
