import abc

from .node import DocumentNode
from .secure_string import SecureString


class DocumentRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, node: DocumentNode) -> None:
        pass

    @abc.abstractmethod
    def get_by_id(self, node_id: str) -> DocumentNode | None:
        pass

    @abc.abstractmethod
    def list_all(self) -> list[DocumentNode]:
        pass


class TransactionManager(abc.ABC):
    @abc.abstractmethod
    def begin(self) -> None:
        pass

    @abc.abstractmethod
    def commit(self) -> None:
        pass

    @abc.abstractmethod
    def rollback(self) -> None:
        pass


class NLPServiceProtocol(abc.ABC):
    @abc.abstractmethod
    def extract_entities(self, text: str) -> list[str]:
        pass

    @abc.abstractmethod
    def summarize(self, text: str) -> str:
        pass


class CredentialProviderProtocol(abc.ABC):
    @abc.abstractmethod
    def get_api_key(self) -> SecureString:
        pass
