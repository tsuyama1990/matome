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

        # 1. Calculate subtree widths (Post-order) - Iterative approach via recursion optimization
        self._calculate_subtree_width_iterative(tree.root_node.id, tree)

        # 2. Assign positions (Pre-order) - Iterative
        self._assign_positions_iterative(tree.root_node.id, 0, 0, tree)

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

    def _calculate_subtree_width_iterative(self, root_id: int | str, tree: "DocumentTree") -> int:
        """
        Iterative post-order traversal to calculate subtree widths.
        Uses a single stack with state tracking to avoid storing full traversal history.
        State: (node_id, children_processed_flag)
        """
        # Stack contains tuples: (node_id, visited_children)
        # visited_children = False means we need to push children.
        # visited_children = True means we process this node (calculate width).
        stack: list[tuple[int | str, bool]] = [(root_id, False)]

        while stack:
            curr_id, children_visited = stack.pop()

            if children_visited:
                # Process the node (calculate width)
                self._process_node_width(curr_id, tree)
            else:
                # Push back with visited=True
                stack.append((curr_id, True))

                # Push children to stack
                children = self._get_children(curr_id, tree)
                for child_idx in reversed(children):
                    stack.append((child_idx, False))

        return self._subtree_widths.get(self._get_node_id_str(root_id), self.NODE_WIDTH)

    def _get_children(self, node_id: int | str, tree: "DocumentTree") -> list[int | str]:
        """Helper to get children IDs."""
        if isinstance(node_id, int):
            return []

        node = tree.all_nodes.get(str(node_id))
        if str(node_id) == tree.root_node.id:
            node = tree.root_node

        if node:
            return node.children_indices
        return []

    def _process_node_width(self, curr_id: int | str, tree: "DocumentTree") -> None:
        """Helper to calculate width for a single node."""
        node_id_str = self._get_node_id_str(curr_id)

        # If Chunk, constant width
        if isinstance(curr_id, int):
            self._subtree_widths[node_id_str] = self.NODE_WIDTH
            return

        # If SummaryNode
        children = self._get_children(curr_id, tree)

        children_widths = [
            self._subtree_widths.get(self._get_node_id_str(child_idx), self.NODE_WIDTH)
            for child_idx in children
        ]

        if not children_widths:
            width = self.NODE_WIDTH
        else:
            total_children_width = sum(children_widths) + self.GAP_X * (len(children_widths) - 1)
            width = max(self.NODE_WIDTH, total_children_width)

        self._subtree_widths[node_id_str] = width

    def _assign_positions_iterative(
        self, root_id: int | str, start_x: int, start_y: int, tree: "DocumentTree"
    ) -> None:
        """
        Iterative pre-order traversal to assign positions.
        Stack stores (node_id, center_x, y).
        """
        stack: list[tuple[int | str, int, int]] = [(root_id, start_x, start_y)]

        while stack:
            curr_id, center_x, y = stack.pop()
            node_id_str = self._get_node_id_str(curr_id)

            # Create Node
            self._create_canvas_node(curr_id, center_x, y, tree)

            # Calculate children positions
            children = self._get_children(curr_id, tree)
            if not children:
                continue

            children_widths = [self._subtree_widths[self._get_node_id_str(c)] for c in children]
            children_block_width = sum(children_widths) + self.GAP_X * (len(children_widths) - 1)

            curr_child_start_x = center_x - (children_block_width / 2)
            next_y = y + self.NODE_HEIGHT + self.GAP_Y

            # We need to calculate x for all children first.
            child_positions = []

            temp_x = curr_child_start_x
            for i, child_idx in enumerate(children):
                child_width = children_widths[i]
                child_center_x = temp_x + (child_width / 2)

                child_positions.append((child_idx, int(child_center_x), next_y))

                # create edge immediately
                child_id_str = self._get_node_id_str(child_idx)
                edge = CanvasEdge(
                    id=f"edge_{node_id_str}_{child_id_str}",
                    fromNode=node_id_str,
                    toNode=child_id_str,
                )
                self.edges.append(edge)

                temp_x += child_width + self.GAP_X

            # Push to stack in reverse
            for item in reversed(child_positions):
                stack.append(item)

    def _create_canvas_node(
        self, node_id: int | str, center_x: int, y: int, tree: "DocumentTree"
    ) -> None:
        """Create and append a CanvasNode."""
        node_id_str = self._get_node_id_str(node_id)

        text = ""
        if isinstance(node_id, int):
            chunk = self._chunk_map.get(node_id)
            chunk_content = chunk.text if chunk else "Missing Chunk"
            text = f"Chunk {node_id}\n\n{chunk_content}"
        else:
            node = tree.all_nodes.get(str(node_id))
            if str(node_id) == tree.root_node.id:
                node = tree.root_node
            text = node.text if node else "Missing Node"

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
