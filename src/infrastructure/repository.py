import threading
from typing import Any

from src.domain_models import DocumentNode, DocumentRepository, TransactionManager


class InMemoryDocumentRepository(DocumentRepository, TransactionManager):
    def __init__(self) -> None:
        self._store: dict[str, DocumentNode] = {}
        self._transaction_active = False
        self._backup_store: dict[str, DocumentNode] = {}
        self._lock = threading.Lock()

    def begin(self) -> None:
        with self._lock:
            self._transaction_active = True
            self._backup_store = self._store.copy()

    def commit(self) -> None:
        with self._lock:
            self._transaction_active = False
            self._backup_store.clear()

    def rollback(self) -> None:
        with self._lock:
            if self._transaction_active:
                self._store = self._backup_store.copy()
                self._transaction_active = False
                self._backup_store.clear()

    def save_node(self, node: DocumentNode) -> None:
        with self._lock:
            self._store[node.id] = node

    def save_nodes(self, nodes: list[DocumentNode]) -> None:
        with self._lock:
            for node in nodes:
                self._store[node.id] = node

    def get_node(self, node_id: str) -> DocumentNode | None:
        with self._lock:
            return self._store.get(node_id)

    def get_children(self, parent_id: str) -> list[DocumentNode]:
        with self._lock:
            return [node for node in self._store.values() if node.parent_id == parent_id]

    def query_nodes(self, filters: dict[str, Any]) -> list[DocumentNode]:
        with self._lock:
            results = []
            for node in self._store.values():
                match = True
                for k, v in filters.items():
                    if getattr(node, k, None) != v:
                        match = False
                        break
                if match:
                    results.append(node)
            return results
