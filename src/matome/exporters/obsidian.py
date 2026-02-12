from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, SummaryNode

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
        # We cache looked-up nodes to avoid repeated DB hits during width calc vs position assignment
        # But for huge trees this is memory risk. However, canvas export usually implies visualizable size.
        # We will use LRU cache or just direct DB hits if performance is okay.
        # For simplicity in this cycle, direct DB hits with simple local cache for the active path?
        # Let's rely on store.get_node which might be cached by OS/SQLite.
        self.config = config or ProcessingConfig()
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

        if not tree.root_node:
            return CanvasFile(nodes=[], edges=[])

        # 1. Calculate subtree widths (Post-order)
        self._calculate_subtree_width(tree.root_node.id, tree, store)

        # 2. Assign positions (Pre-order)
        # Root starts at (0, 0)
        self._assign_positions(tree.root_node.id, 0, 0, tree, store)

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
            f.write(canvas_file.model_dump_json(indent=2, by_alias=True, exclude_none=True))

    def _get_node_id_str(self, node_id: int | str) -> str:
        """Converts internal node ID to canvas node ID."""
        if isinstance(node_id, int):
            return f"chunk_{node_id}"
        return node_id

    def _get_node(self, node_id: int | str, tree: "DocumentTree", store: "DiskChunkStore | None") -> Chunk | SummaryNode | None:
        """Helper to retrieve node from tree root, memory dict, or store."""
        if isinstance(node_id, str):
            if node_id == tree.root_node.id:
                return tree.root_node
            if tree.all_nodes and node_id in tree.all_nodes:
                return tree.all_nodes[node_id]

        if store:
            obj = store.get_node(node_id)
            if isinstance(obj, (Chunk, SummaryNode)):
                return obj

        return None

    def _calculate_subtree_width(self, root_id: int | str, tree: "DocumentTree", store: "DiskChunkStore | None") -> int:
        """
        Iteratively calculates the width of the subtree rooted at node_id using a stack.
        Avoids recursion depth limits.
        """
        # Post-order traversal preparation
        processing_order = self._get_traversal_order(root_id, tree, store)

        # Process in reverse (bottom-up) to calculate widths
        for curr_id in reversed(processing_order):
            self._process_node_width(curr_id, tree, store)

        return self._subtree_widths[self._get_node_id_str(root_id)]

    def _get_traversal_order(self, root_id: int | str, tree: "DocumentTree", store: "DiskChunkStore | None") -> list[int | str]:
        """Helper to get processing order for nodes."""
        stack = [root_id]
        processing_order: list[int | str] = []

        while stack:
            curr_id = stack.pop()
            processing_order.append(curr_id)

            if isinstance(curr_id, str):
                self._append_children_to_stack(curr_id, stack, tree, store)
        return processing_order

    def _append_children_to_stack(
        self, curr_id: str, stack: list[int | str], tree: "DocumentTree", store: "DiskChunkStore | None"
    ) -> None:
        """Helper to push children to stack."""
        node = self._get_node(curr_id, tree, store)

        if isinstance(node, SummaryNode):
            for child_idx in node.children_indices:
                stack.append(child_idx)

    def _process_node_width(self, curr_id: int | str, tree: "DocumentTree", store: "DiskChunkStore | None") -> None:
        """Helper to calculate width for a single node."""
        node_id_str = self._get_node_id_str(curr_id)

        # If Chunk
        if isinstance(curr_id, int):
            self._subtree_widths[node_id_str] = self.NODE_WIDTH
            return

        # If SummaryNode
        node = self._get_node(curr_id, tree, store)

        if not isinstance(node, SummaryNode):
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
        self, node_id: int | str, center_x: int, y: int, tree: "DocumentTree", store: "DiskChunkStore | None"
    ) -> None:
        """Recursively assigns (x, y) positions to nodes and creates edges."""
        node_id_str = self._get_node_id_str(node_id)

        node = self._get_node(node_id, tree, store)
        text = "Missing Node"
        if node:
            text = node.text
            if isinstance(node, Chunk):
                text = f"Chunk {node.index}\n\n{text}"

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
        if isinstance(node, Chunk) or not isinstance(node, SummaryNode):
            return

        # If SummaryNode, process children
        children = node.children_indices
        if not children:
            return

        # Calculate starting x for children
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
            self._assign_positions(child_idx, int(child_center_x), next_y, tree, store)

            # Create Edge
            edge = CanvasEdge(
                id=f"edge_{node_id_str}_{child_id_str}", from_node=node_id_str, to_node=child_id_str
            )
            self.edges.append(edge)

            # Advance x
            current_x += child_width + self.GAP_X
