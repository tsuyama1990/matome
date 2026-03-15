from src.domain_models import LearningProgress, RaptorNode
from src.domain_models.exceptions import ProcessingError
from src.interfaces.dependencies import LLMProtocol


class SQ3REngine:
    """
    Engine for interactive Question and Recite features in the SQ3R loop.
    Generates questions to unlock nodes, and evaluates user recited summaries.
    """

    def __init__(self, llm: LLMProtocol) -> None:
        self._llm = llm

    async def generate_question(self, node: RaptorNode, difficulty: str = "medium") -> str:
        """Generates a contextual question based on the node's hidden summary."""
        prompt = (
            f"Based on the following summary, generate a single, thought-provoking question "
            f"at a '{difficulty}' difficulty level that tests the reader's understanding of "
            f"the core concept. The question should not directly reveal the answer.\n\n"
            f"Summary: {node.summarized_content}\n\n"
            "Question:"
        )
        try:
            # We must use generate_text to be compatible with LLMProtocol which requires a model
            question = await self._llm.generate_text(prompt, model="default")
            return question.strip()
        except Exception as e:
            msg = "Failed to generate question."
            raise ProcessingError(msg) from e

    async def evaluate_answer(self, node: RaptorNode, user_answer: str) -> bool:
        """Evaluates the user's answer against the node's summary."""
        import bleach

        # Add input sanitization and length validation before LLM call
        if len(user_answer) > 10000:
            msg = "Answer too long"
            raise ValueError(msg)

        sanitized_answer = bleach.clean(
            user_answer, tags=[], attributes={}, protocols=[], strip=True
        )

        prompt = (
            "You are an AI tutor. A student has just read the following summary and provided an answer "
            "to a question about it. Given this source text and this user's answer to a question about it, "
            "is the user's answer fundamentally correct or demonstrating understanding? "
            "Respond only with 'YES' or 'NO'.\n\n"
            f"Original Summary: {node.summarized_content}\n"
            f"Student Answer: {sanitized_answer}\n\n"
            "Evaluation:"
        )
        try:
            evaluation = await self._llm.generate_text(prompt, model="default")
            # Parse the LLM's response to return a boolean indicating success or failure
            return "yes" in evaluation.lower()
        except Exception as e:
            msg = "Failed to evaluate answer."
            raise ProcessingError(msg) from e

    def unlock_node(self, progress: LearningProgress, node_id: str) -> LearningProgress:
        """Updates the LearningProgress state by adding the node_id to the unlocked_node_ids set."""
        progress.unlocked_node_ids.add(node_id)
        return progress


class SQ3RService:
    def __init__(self, engine: SQ3REngine) -> None:
        self.engine = engine

    async def get_question(self, node: RaptorNode) -> str:
        return await self.engine.generate_question(node)

    async def unlock_node(self, node: RaptorNode, user_answer: str) -> str:
        feedback = await self.engine.evaluate_answer(node, user_answer)
        node.is_unlocked = feedback
        return "Good job. You are correct." if feedback else "Locked"
