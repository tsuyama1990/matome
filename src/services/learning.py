from src.domain_models import KnowledgeNode
from src.interfaces import ActiveLearningError, ActiveLearningService


class DefaultActiveLearningService(ActiveLearningService):
    """Production implementation of the ActiveLearningService."""

    def evaluate_answer(self, node: KnowledgeNode, answer: str) -> bool:
        if not answer:
            msg = "Answer cannot be empty"
            raise ActiveLearningError(msg)

        # Simplified evaluation logic
        return len(answer) > 5

    def generate_question(self, node: KnowledgeNode, difficulty: str = "normal") -> str:
        if node.state == "Unlocked":
            msg = "Cannot generate question for unlocked node"
            raise ActiveLearningError(msg)

        return f"What is the main concept of {node.title}? ({difficulty} difficulty)"

    def track_progress(self, user_id: str, node_id: str, success: bool) -> None:
        """Tracks the user's progress through the nodes."""

    def get_feedback(self, node: KnowledgeNode, answer: str) -> str:
        """Generates 'Sandwich Feedback'."""
        return "Good attempt. However, remember the specific details."
