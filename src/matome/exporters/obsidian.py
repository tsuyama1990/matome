from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk

if TYPE_CHECKING:
    from domain_models.manifest import DocumentTree
    from matome.utils.store import DiskChunkStore


class CanvasNode(BaseModel):
    """Represents a node in the Obsidian Canvas."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the node.")
    x: int = Field(..., description="X coordinate of the node.")
    y: int = Field(..., description="Y coordinate of the node.")
    width: int = Field(..., description="Width of the node.")
    height: int = Field(..., description="Height of the node.")
    type: Literal["text", "file", "group"] = Field(default="text", description="Type of the node.")
    text: str | None = Field(default=None, description="Text content for text nodes.")


class CanvasEdge(BaseModel):
    """Represents an edge (connection) between nodes in the Obsidian Canvas."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(..., description="Unique identifier for the edge.")
    from_node: str = Field(..., alias="fromNode", description="ID of the source node.")
    to_node: str = Field(..., alias="toNode", description="ID of the target node.")


class CanvasFile(BaseModel):
    """Represents the entire Obsidian Canvas file structure."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[CanvasNode] = Field(..., description="List of nodes in the canvas.")
    edges: list[CanvasEdge] = Field(..., description="List of edges in the canvas.")


class ObsidianCanvasExporter:
    """Exports DocumentTree to Obsidian Canvas format."""

    def __init__(self, config: ProcessingConfig | None = None) -> None:
        self.nodes: list[CanvasNode] = []
        self.edges: list[CanvasEdge] = []
        self._subtree_widths: dict[str, int] = {}
        self._chunk_map: dict[int, Chunk] = {}
        self.config = config or ProcessingConfig()
        # Use config values instead of hardcoded defaults if they were hardcoded before
        # In the provided read_file output, they are already using config.
        # However, the audit said "Hardcoded constants for canvas dimensions and gaps in ObsidianCanvasExporter".
        # Checking lines 34-37 in previous read:
        # self.NODE_WIDTH = self.config.canvas_node_width
        # ...
        # It seems they ARE using config now.
        # Perhaps the audit referred to a version where they were hardcoded?
        # Or maybe the audit meant I should REMOVE local constants and use config directly?
        # I will keep them as instance variables for readability but ensure they come from config.
        self.NODE_WIDTH = self.config.canvas_node_width
        self.NODE_HEIGHT = self.config.canvas_node_height
        self.GAP_X = self.config.canvas_gap_x
        self.GAP_Y = self.config.canvas_gap_y

    def generate_canvas_data(
        self, tree: "DocumentTree", store: "DiskChunkStore | None" = None
    ) -> CanvasFile:
        """
        Generates the canvas data structure from the document tree.

        Args:
            tree: The DocumentTree to export.
            store: Optional DiskChunkStore to retrieve leaf chunk text.
                   If None, leaf chunks will be missing text.
        """
        self.nodes = []
        self.edges = []
        self._subtree_widths = {}
        self._chunk_map = {}

        # Populate chunk map from store if available
        if store and tree.leaf_chunk_ids:
            for chunk_id in tree.leaf_chunk_ids:
                node = store.get_node(chunk_id)
                if isinstance(node, Chunk):
                    self._chunk_map[node.index] = node

        if not tree.root_node:
            return CanvasFile(nodes=[], edges=[])

        # 1. Calculate subtree widths (Post-order)
        self._calculate_subtree_width(tree.root_node.id, tree)

        # 2. Assign positions (Pre-order)
        # Root starts at (0, 0)
        self._assign_positions(tree.root_node.id, 0, 0, tree)

        return CanvasFile(nodes=self.nodes, edges=self.edges)

    def export(
        self, tree: "DocumentTree", output_path: Path, store: "DiskChunkStore | None" = None
    ) -> None:
        """
        Exports the canvas to a file.

        Args:
            tree: The DocumentTree to export.
            output_path: Destination path for the .canvas file.
            store: Optional DiskChunkStore to retrieve leaf chunk text.
        """
        canvas_file = self.generate_canvas_data(tree, store)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            # exclude_none=True to avoid dumping optional fields as null if not needed
            # by_alias=True to use fromNode/toNode
            f.write(canvas_file.model_dump_json(indent=2, by_alias=True, exclude_none=True))

    def _get_node_id_str(self, node_id: int | str) -> str:
        """Converts internal node ID to canvas node ID."""
        if isinstance(node_id, int):
            return f"chunk_{node_id}"
        return node_id

    def _calculate_subtree_width(self, root_id: int | str, tree: "DocumentTree") -> int:
        """
        Iteratively calculates the width of the subtree rooted at node_id using a stack.
        Avoids recursion depth limits.
        """
        # Post-order traversal preparation
        processing_order = self._get_traversal_order(root_id, tree)

        # Process in reverse (bottom-up) to calculate widths
        for curr_id in reversed(processing_order):
            self._process_node_width(curr_id, tree)

        return self._subtree_widths[self._get_node_id_str(root_id)]

    def _get_traversal_order(self, root_id: int | str, tree: "DocumentTree") -> list[int | str]:
        """Helper to get processing order for nodes."""
        stack = [root_id]
        processing_order: list[int | str] = []

        while stack:
            curr_id = stack.pop()
            processing_order.append(curr_id)

            if isinstance(curr_id, str):
                self._append_children_to_stack(curr_id, stack, tree)
        return processing_order

    def _append_children_to_stack(
        self, curr_id: str, stack: list[int | str], tree: "DocumentTree"
    ) -> None:
        """Helper to push children to stack."""
        node = tree.all_nodes.get(curr_id)
        if curr_id == tree.root_node.id:
            node = tree.root_node

        if node:
            for child_idx in node.children_indices:
                stack.append(child_idx)

    def _process_node_width(self, curr_id: int | str, tree: "DocumentTree") -> None:
        """Helper to calculate width for a single node."""
        node_id_str = self._get_node_id_str(curr_id)

        # If Chunk
        if isinstance(curr_id, int):
            self._subtree_widths[node_id_str] = self.NODE_WIDTH
            return

        # If SummaryNode
        node = tree.all_nodes.get(str(curr_id))
        if str(curr_id) == tree.root_node.id:
            node = tree.root_node

        if not node:
            self._subtree_widths[node_id_str] = self.NODE_WIDTH
            return

        children_widths = [
            self._subtree_widths.get(self._get_node_id_str(child_idx), self.NODE_WIDTH)
            for child_idx in node.children_indices
        ]

        if not children_widths:
            width = self.NODE_WIDTH
        else:
            total_children_width = sum(children_widths) + self.GAP_X * (len(children_widths) - 1)
            width = max(self.NODE_WIDTH, total_children_width)

        self._subtree_widths[node_id_str] = width

    def _assign_positions(
        self, node_id: int | str, center_x: int, y: int, tree: "DocumentTree"
    ) -> None:
        """Recursively assigns (x, y) positions to nodes and creates edges."""
        node_id_str = self._get_node_id_str(node_id)

        # Create the node
        text = ""
        if isinstance(node_id, int):
            chunk = self._chunk_map.get(node_id)
            chunk_content = chunk.text if chunk else "Missing Chunk"
            text = f"Chunk {node_id}\n\n{chunk_content}"
        else:
            # Summary Node
            node = tree.all_nodes.get(str(node_id))
            if str(node_id) == tree.root_node.id:
                node = tree.root_node
            text = node.text if node else "Missing Node"

        # Position: center_x is the center of the node.
        # Canvas x is the top-left corner.
        x = center_x - (self.NODE_WIDTH // 2)

        canvas_node = CanvasNode(
            id=node_id_str,
            x=int(x),
            y=y,
            width=self.NODE_WIDTH,
            height=self.NODE_HEIGHT,
            type="text",
            text=text,
        )
        self.nodes.append(canvas_node)

        # If Chunk, we are done
        if isinstance(node_id, int):
            return

        # If SummaryNode, process children
        summary_node = tree.all_nodes.get(str(node_id))
        if str(node_id) == tree.root_node.id:
            summary_node = tree.root_node

        if not summary_node:
            return

        children = summary_node.children_indices
        if not children:
            return

        # Calculate starting x for children
        # We want to center the children block under the parent
        # The children block width is what we calculated in _calculate_subtree_width
        # But wait, subtree_width logic in step 1 was: max(NODE_WIDTH, children_total_width)
        # So we need the actual children total width to center them.

        children_widths = [self._subtree_widths[self._get_node_id_str(c)] for c in children]
        children_block_width = sum(children_widths) + self.GAP_X * (len(children_widths) - 1)

        start_x = center_x - (children_block_width / 2)
        current_x = start_x

        next_y = y + self.NODE_HEIGHT + self.GAP_Y

        for child_idx in children:
            child_id_str = self._get_node_id_str(child_idx)
            child_width = self._subtree_widths[child_id_str]

            # Child center
            child_center_x = current_x + (child_width / 2)

            # Recurse
            self._assign_positions(child_idx, int(child_center_x), next_y, tree)

            # Create Edge
            edge = CanvasEdge(
                id=f"edge_{node_id_str}_{child_id_str}", fromNode=node_id_str, toNode=child_id_str
            )
            self.edges.append(edge)

            # Advance x
            current_x += child_width + self.GAP_X
