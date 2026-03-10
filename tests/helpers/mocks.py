from src.domain_models import (
    AIServiceProtocol,
    ContentNode,
    IdentityNode,
    PivotBoard,
    UserInteractionContext,
)


class MockAIService(AIServiceProtocol):
    """Mock implementation of the AIServiceProtocol for testing and isolated pipelines."""

    def generate_summary(self, content: str) -> str:
        return "1. System Actor: Approver\n2. Key Constraint: budget > 5000\n3. Action: Approval required."

    def generate_question(self, identity: IdentityNode, content: ContentNode) -> str:
        return f"What is the key point of {identity.title}?"

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        return f"graph TD;\n  A[{board.original_root_id}]-->B[Workflow];"

    def generate_markdown_requirements(self, board: PivotBoard) -> str:
        return f"# PRD\n\nGenerated for board {board.id}."

    def verify_web_grounding(self, content: str) -> str:
        return "Web grounding verification complete: The statements align with modern SaaS best practices."

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        if context.user_answer and "budget > 5000" in context.user_answer:
            return True, "Correct!"
        return False, "Incorrect."
