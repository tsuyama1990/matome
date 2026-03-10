import abc

from src.domain_models.node import DocumentNode
from src.domain_models.secure_string import SecureString


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


class UserRepository(abc.ABC):
    @abc.abstractmethod
    def get_user(self, user_id: str) -> dict[str, str] | None:
        pass


class VectorDBProtocol(abc.ABC):
    @abc.abstractmethod
    def search(self, query: str) -> list[DocumentNode]:
        pass


class AIGatewayProtocol(abc.ABC):
    @abc.abstractmethod
    def generate(self, prompt: str) -> str:
        pass


class NLPServiceProtocol(abc.ABC):
    @abc.abstractmethod
    def extract_entities(self, text: str) -> list[str]:
        pass

    @abc.abstractmethod
    def summarize(self, text: str) -> str:
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


class CredentialProviderProtocol(abc.ABC):
    @abc.abstractmethod
    def get_api_key(self) -> SecureString:
        pass
