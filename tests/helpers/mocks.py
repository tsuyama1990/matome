from src.domain_models import AIServiceProtocol, DocumentNode, PivotBoard, UserInteractionContext


class MockAIService(AIServiceProtocol):
    """Mock implementation of the AIServiceProtocol for testing and isolated pipelines."""

    def generate_summary(self, content: str) -> str:
        return "1. System Actor: Approver\n2. Key Constraint: budget > 5000\n3. Action: Approval required."

    def generate_question(self, node: DocumentNode) -> str:
        return f"What is the key point of {node.title}?"

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        return f"graph TD;\n  A[{board.original_root_id}]-->B[Workflow];"

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        if context.user_answer and "budget > 5000" in context.user_answer:
            return True, "Correct!"
        return False, "Incorrect."
