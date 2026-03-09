from typing import Any

from src.domain_models import DocumentNode, DocumentQueryService, DocumentRepository


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._store: dict[str, DocumentNode] = {}

    def save_node(self, node: DocumentNode) -> None:
        self._store[node.id] = node

    def save_nodes(self, nodes: list[DocumentNode]) -> None:
        for node in nodes:
            self.save_node(node)

    def get_node(self, node_id: str) -> DocumentNode | None:
        return self._store.get(node_id)

    def get_children(self, parent_id: str) -> list[DocumentNode]:
        return [node for node in self._store.values() if node.parent_id == parent_id]


class InMemoryDocumentQueryService(DocumentQueryService):
    def __init__(self, repository: InMemoryDocumentRepository) -> None:
        self.repository = repository

    def query_nodes(self, filters: dict[str, Any]) -> list[DocumentNode]:
        results = []
        for node in self.repository._store.values():
            match = True
            for k, v in filters.items():
                if getattr(node, k, None) != v:
                    match = False
                    break
            if match:
                results.append(node)
        return results
