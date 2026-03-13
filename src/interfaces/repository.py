from typing import Protocol

from src.domain_models.document import RaptorNode


class DocumentRepositoryProtocol(Protocol):
    def get_node_by_id(self, node_id: str) -> RaptorNode: ...
    def save_node(self, node: RaptorNode) -> None: ...
