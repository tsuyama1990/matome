from src.application import SQ3REngine
from src.domain_models import RaptorNode
from src.interfaces.dependencies import LLMProtocol


class SQ3RService:
    def __init__(self, llm: LLMProtocol) -> None:
        self.engine = SQ3REngine(llm=llm)

    async def get_question(self, node: RaptorNode) -> str:
        return await self.engine.generate_question(node)

    async def unlock_node(self, node: RaptorNode, user_answer: str) -> str:
        feedback = await self.engine.evaluate_answer(user_answer, node)
        node.is_unlocked = True
        return feedback
