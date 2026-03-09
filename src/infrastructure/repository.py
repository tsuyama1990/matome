import threading

from src.domain_models import ContentNode, DocumentRepository, IdentityNode, TransactionManager


class InMemoryDocumentRepository(DocumentRepository, TransactionManager):
    def __init__(self) -> None:
        self._identities: dict[str, IdentityNode] = {}
        self._contents: dict[str, ContentNode] = {}
        self._transaction_active = False
        self._backup_identities: dict[str, IdentityNode] = {}
        self._backup_contents: dict[str, ContentNode] = {}
        self._lock = threading.Lock()

    def begin(self) -> None:
        with self._lock:
            self._transaction_active = True
            self._backup_identities = self._identities.copy()
            self._backup_contents = self._contents.copy()

    def commit(self) -> None:
        with self._lock:
            self._transaction_active = False
            self._backup_identities.clear()
            self._backup_contents.clear()

    def rollback(self) -> None:
        with self._lock:
            if self._transaction_active:
                self._identities = self._backup_identities.copy()
                self._contents = self._backup_contents.copy()
                self._transaction_active = False
                self._backup_identities.clear()
                self._backup_contents.clear()

    def save_identity(self, node: IdentityNode) -> None:
        with self._lock:
            self._identities[node.id] = node

    def save_content(self, node: ContentNode) -> None:
        with self._lock:
            self._contents[node.node_id] = node

    def get_identity(self, node_id: str) -> IdentityNode | None:
        with self._lock:
            return self._identities.get(node_id)

    def get_content(self, node_id: str) -> ContentNode | None:
        with self._lock:
            return self._contents.get(node_id)

    def get_children(self, parent_id: str) -> list[IdentityNode]:
        with self._lock:
            return [node for node in self._identities.values() if node.parent_id == parent_id]
