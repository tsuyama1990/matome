import sys

from src.domain_models import (
    DocumentNode,
    NodeStatus,
    PivotAxis,
    PivotBoard,
    PivotBoardNode,
    UserInteractionContext,
)


def simulate_user_journey() -> None:
    """
    Simulates a new user uploading a manual and transforming it.
    """
    # Step 1: Ingestion
    sys.stdout.write("User uploads manual: test_text.txt\n")
    doc_node = DocumentNode(
        id="root_1",
        parent_id=None,
        title="Complex Business Manual",
        summary=None,
        content=None,
        status=NodeStatus.LOCKED,
        metadata={"category": "business"}
    )

    # Step 2: Interaction
    sys.stdout.write(f"User interacts with: {doc_node.title}\n")
    ctx = UserInteractionContext(
        node_id=doc_node.id,
        status=NodeStatus.LOCKED,
        question_asked="What condition requires executive approval?",
        user_answer="If budget > 5000",
        feedback="Correct. Node Unlocked.",
        hints_used=0
    )
    doc_node.status = NodeStatus.UNLOCKED
    sys.stdout.write(f"Node {ctx.node_id} Unlocked. Summary shown to user.\n")

    # Step 3: Pivot
    sys.stdout.write("User pivots node into Actor/State layout\n")
    board = PivotBoard(
        id="board_1",
        original_root_id=doc_node.id,
        axis=PivotAxis.ACTOR_STATE,
        custom_axis_description=None,
        nodes=[
            PivotBoardNode(node_id=doc_node.id, x_position=0.0, y_position=1.0, cluster_id="actor_ceo")
        ],
        mermaid_diagram="sequenceDiagram..."
    )
    sys.stdout.write(f"Successfully generated {board.axis.value} diagram.\n")

if __name__ == "__main__":
    simulate_user_journey()
