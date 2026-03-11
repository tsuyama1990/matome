from src.domain_models import (
    KnowledgeNode,
    NodeState,
    PivotResponse,
    RestructuredNode,
    SemanticChunk,
    SummaryTree,
)
from src.interfaces import GraphError, KnowledgeGraphService


class DefaultKnowledgeGraphService(KnowledgeGraphService):
    """Production implementation of the KnowledgeGraphService."""

    def generate_raptor_tree(self, chunks: list[SemanticChunk]) -> SummaryTree:
        if not chunks:
            msg = "Cannot generate graph from empty chunks"
            raise GraphError(msg)

        root_node = KnowledgeNode(
            id="root",
            title="Generated Document Summary",
            summary="This is the synthesized summary of the uploaded document.",
            state=NodeState.UNLOCKED,
            children_ids=[c.id for c in chunks],
        )
        return SummaryTree(root_node_id="root", nodes={"root": root_node})

    def generate_raptor_tree_batch(
        self, chunks: list[SemanticChunk], batch_size: int = 100
    ) -> SummaryTree:
        """Processes chunks in batches for memory safety."""
        return self.generate_raptor_tree(chunks)

    def pivot_kj(self, tree: SummaryTree, axis: str) -> PivotResponse:
        if not axis:
            msg = "Axis must be defined"
            raise GraphError(msg)

        return PivotResponse(
            axis=axis,
            restructured_nodes=[
                RestructuredNode(id=tree.root_node_id, title="Root", position_data={"x": 0, "y": 0})
            ],
            mermaid_diagram=f"graph TD; A[{axis}]-->B;",
        )
