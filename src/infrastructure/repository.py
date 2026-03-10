import threading

from src.domain_models import (
    AIMetadataContainer,
    ContentNode,
    DocumentRepository,
    IdentityNode,
    MetadataRepository,
    NodeMetadataContainer,
    TransactionManager,
)


class InMemoryDocumentRepository(DocumentRepository, TransactionManager, MetadataRepository):
    def __init__(self) -> None:
        self._identities: dict[str, IdentityNode] = {}
        self._contents: dict[str, ContentNode] = {}
        self._node_metadata: dict[str, NodeMetadataContainer] = {}
        self._ai_metadata: dict[str, AIMetadataContainer] = {}
        self._transaction_active = False
        self._backup_identities: dict[str, IdentityNode] = {}
        self._backup_contents: dict[str, ContentNode] = {}
        self._backup_node_metadata: dict[str, NodeMetadataContainer] = {}
        self._backup_ai_metadata: dict[str, AIMetadataContainer] = {}
        self._lock = threading.Lock()

    def begin(self) -> None:
        with self._lock:
            self._transaction_active = True
            self._backup_identities = self._identities.copy()
            self._backup_contents = self._contents.copy()
            self._backup_node_metadata = self._node_metadata.copy()
            self._backup_ai_metadata = self._ai_metadata.copy()

    def commit(self) -> None:
        with self._lock:
            self._transaction_active = False
            self._backup_identities.clear()
            self._backup_contents.clear()
            self._backup_node_metadata.clear()
            self._backup_ai_metadata.clear()

    def rollback(self) -> None:
        with self._lock:
            if self._transaction_active:
                self._identities = self._backup_identities.copy()
                self._contents = self._backup_contents.copy()
                self._node_metadata = self._backup_node_metadata.copy()
                self._ai_metadata = self._backup_ai_metadata.copy()
                self._transaction_active = False
                self._backup_identities.clear()
                self._backup_contents.clear()
                self._backup_node_metadata.clear()
                self._backup_ai_metadata.clear()

    def get_node_metadata(self, node_id: str) -> NodeMetadataContainer | None:
        with self._lock:
            return self._node_metadata.get(node_id)

    def get_ai_metadata(self, node_id: str) -> AIMetadataContainer | None:
        with self._lock:
            return self._ai_metadata.get(node_id)

    def save_node_metadata(self, metadata: NodeMetadataContainer) -> None:
        with self._lock:
            self._node_metadata[metadata.node_id] = metadata

    def save_ai_metadata(self, metadata: AIMetadataContainer) -> None:
        with self._lock:
            self._ai_metadata[metadata.node_id] = metadata

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
