from src.domain_models import GraphState, KnowledgeNode
from src.interfaces import ActiveLearningService, KnowledgeGraphService


class BaseTestKnowledgeGraphService(KnowledgeGraphService):
    """Minimal test implementation that returns predictable results."""

    def generate_raptor_tree(self, state: GraphState) -> GraphState:
        return state

    def generate_raptor_tree_batch(self, state: GraphState, batch_size: int = 100) -> GraphState:
        return state

    def pivot_kj(self, state: GraphState) -> GraphState:
        return state


class BaseTestActiveLearningService(ActiveLearningService):
    """Minimal test implementation with predictable behavior."""

    def evaluate_answer(self, node: KnowledgeNode, answer: str) -> bool:
        return "test" in answer.lower()

    def generate_question(self, node: KnowledgeNode, difficulty: str = "normal") -> str:
        return f"Test question about: {node.title[:50]}..."

    def track_progress(self, user_id: str, node_id: str, success: bool) -> None:
        return None

    def get_feedback(self, node: KnowledgeNode, answer: str) -> str:
        return "Test feedback for your answer."
