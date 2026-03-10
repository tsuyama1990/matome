from src.domain_models import (
    AIServiceProtocol,
    ContentNode,
    IdentityNode,
    PivotBoard,
    UserInteractionContext,
)


class MockAIService(AIServiceProtocol):
    """Mock implementation of the AIServiceProtocol for testing and isolated pipelines."""

    def __init__(
        self,
        summary_response: str = "1. System Actor: Approver\n2. Key Constraint: budget > 5000\n3. Action: Approval required.",
        mermaid_response: str | None = None,
        markdown_response: str | None = None,
        web_grounding_response: str = "Web grounding verification complete: The statements align with modern SaaS best practices.",
        evaluate_answer_success: bool = True,
        evaluate_answer_feedback: str = "Correct!",
    ) -> None:
        self.summary_response = summary_response
        self.mermaid_response = mermaid_response
        self.markdown_response = markdown_response
        self.web_grounding_response = web_grounding_response
        self.evaluate_answer_success = evaluate_answer_success
        self.evaluate_answer_feedback = evaluate_answer_feedback

    def generate_summary(self, content: str) -> str:
        return self.summary_response

    def generate_question(self, identity: IdentityNode, content: ContentNode) -> str:
        return f"What is the key point of {identity.title}?"

    def generate_mermaid_diagram(self, board: PivotBoard) -> str:
        return self.mermaid_response or f"graph TD;\n  A[{board.original_root_id}]-->B[Workflow];"

    def generate_markdown_requirements(self, board: PivotBoard) -> str:
        return self.markdown_response or f"# PRD\n\nGenerated for board {board.id}."

    def verify_web_grounding(self, content: str) -> str:
        return self.web_grounding_response

    def evaluate_answer(self, context: UserInteractionContext) -> tuple[bool, str]:
        if context.user_answer and "budget > 5000" in context.user_answer:
            return self.evaluate_answer_success, self.evaluate_answer_feedback
        return False, "Incorrect."
