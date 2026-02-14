from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, SummaryNode
from matome.utils.store import DiskChunkStore

if TYPE_CHECKING:
    from domain_models.manifest import DocumentTree


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
        self.config = config or ProcessingConfig()
        self.NODE_WIDTH = self.config.canvas_node_width
        self.NODE_HEIGHT = self.config.canvas_node_height
        self.GAP_X = self.config.canvas_gap_x
        self.GAP_Y = self.config.canvas_gap_y

    def generate_canvas_data(
        self, tree: "DocumentTree", store: "DiskChunkStore"
    ) -> CanvasFile:
        """
        Generates the canvas data structure from the document tree.

        Args:
            tree: The DocumentTree to export.
            store: DiskChunkStore to retrieve nodes (required).
        """
        self.nodes = []
        self.edges = []
        self._subtree_widths = {}

        if not tree.root_node:
            return CanvasFile(nodes=[], edges=[])

        # 1. Calculate subtree widths (Post-order)
        self._calculate_subtree_width(tree.root_node.id, store)

        # 2. Assign positions (Pre-order)
        # Root starts at (0, 0)
        self._assign_positions(tree.root_node.id, 0, 0, store)

        return CanvasFile(nodes=self.nodes, edges=self.edges)

    def export(
        self, tree: "DocumentTree", output_path: Path, store: "DiskChunkStore"
    ) -> None:
        """
        Exports the canvas to a file.

        Args:
            tree: The DocumentTree to export.
            output_path: Destination path for the .canvas file.
            store: DiskChunkStore to retrieve nodes.
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

    def _calculate_subtree_width(self, root_id: int | str, store: DiskChunkStore) -> int:
        """
        Iteratively calculates the width of the subtree rooted at node_id using a stack.
        Avoids recursion depth limits.
        """
        # Post-order traversal preparation
        processing_order = self._get_traversal_order(root_id, store)

        # Process in reverse (bottom-up) to calculate widths
        for curr_id in reversed(processing_order):
            self._process_node_width(curr_id, store)

        return self._subtree_widths[self._get_node_id_str(root_id)]

    def _get_traversal_order(
        self, root_id: int | str, store: DiskChunkStore
    ) -> list[int | str]:
        """Helper to get processing order for nodes."""
        stack = [root_id]
        processing_order: list[int | str] = []
        visited = set()

        while stack:
            curr_id = stack.pop()
            if curr_id in visited:
                continue
            visited.add(curr_id)
            processing_order.append(curr_id)

            # Push children to stack
            node = store.get_node(curr_id)
            if isinstance(node, SummaryNode):
                # Reverse to process left-to-right? Stack is LIFO.
                # If we want order, we push reversed.
                for child_idx in node.children_indices:
                    stack.append(child_idx)

        return processing_order

    def _process_node_width(self, curr_id: int | str, store: DiskChunkStore) -> None:
        """Helper to calculate width for a single node."""
        node_id_str = self._get_node_id_str(curr_id)

        node = store.get_node(curr_id)

        # If Chunk or missing
        if isinstance(node, Chunk) or not node:
            self._subtree_widths[node_id_str] = self.NODE_WIDTH
            return

        # If SummaryNode
        if isinstance(node, SummaryNode):
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
        self, root_id: int | str, start_center_x: int, start_y: int, store: DiskChunkStore
    ) -> None:
        """
        Iteratively assigns (x, y) positions to nodes and creates edges using a stack.
        """
        # Stack stores (node_id, center_x, y)
        stack: list[tuple[int | str, int, int]] = [(root_id, start_center_x, start_y)]

        while stack:
            node_id, center_x, y = stack.pop()
            node_id_str = self._get_node_id_str(node_id)
            node = store.get_node(node_id)

            text = "Missing Node"
            if isinstance(node, Chunk):
                text = f"Chunk {node.index}\n\n{node.text}"
            elif isinstance(node, SummaryNode):
                text = node.text

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

            if not isinstance(node, SummaryNode):
                continue

            children = node.children_indices
            if not children:
                continue

            children_widths = [self._subtree_widths.get(self._get_node_id_str(c), self.NODE_WIDTH) for c in children]
            children_block_width = sum(children_widths) + self.GAP_X * (len(children_widths) - 1)

            start_x = center_x - (children_block_width / 2)
            current_x = start_x

            next_y = y + self.NODE_HEIGHT + self.GAP_Y

            # Prepare children to push to stack
            # Since stack is LIFO, we want to process left child first?
            # Actually, standard DFS order usually processes left first.
            # But here we are just adding to lists.
            # BUT we need to calculate `current_x` sequentially for each child.
            # We can calculate all children positions NOW, and push them.

            # We must iterate children in order to calculate positions correctly
            for child_idx in children:
                child_id_str = self._get_node_id_str(child_idx)
                child_width = self._subtree_widths.get(child_id_str, self.NODE_WIDTH)

                child_center_x = current_x + (child_width / 2)

                # Create edge here
                edge = CanvasEdge(
                    id=f"edge_{node_id_str}_{child_id_str}", from_node=node_id_str, to_node=child_id_str
                )
                self.edges.append(edge)

                # Push to stack
                # Note: If we push sequentially, last child is popped first.
                # Does it matter? Position (x,y) is already calculated.
                # So popping order only affects the order in JSON list.
                stack.append((child_idx, int(child_center_x), next_y))

                current_x += child_width + self.GAP_X
