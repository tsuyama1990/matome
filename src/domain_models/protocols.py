from typing import Protocol

from pydantic import SecretStr

from .node import ContentNode, IdentityNode


class DocumentRepository(Protocol):
    """Protocol for transactional document storage."""

    def save_identity_node(self, node: IdentityNode) -> None: ...

    def get_identity_node(self, node_id: str) -> IdentityNode | None: ...

    def save_content_node(self, node: ContentNode) -> None: ...

    def get_content_node(self, node_id: str) -> ContentNode | None: ...


class UserRepository(Protocol):
    """Protocol for transactional user and session storage."""

    def get_user_state(self, user_id: str) -> dict[str, str]: ...

    def save_user_state(self, user_id: str, state: dict[str, str]) -> None: ...


class VectorDBProtocol(Protocol):
    """Protocol for vector database operations."""

    def upsert_embedding(
        self, node_id: str, embedding: list[float], metadata: dict[str, str]
    ) -> None: ...

    def search_similar(self, query_embedding: list[float], top_k: int) -> list[str]: ...


class AIGatewayProtocol(Protocol):
    """Protocol for abstracting external AI model communications."""

    def generate_embedding(self, text: str) -> list[float]: ...

    def complete_prompt(self, prompt: str, model: str | None = None) -> str: ...


class CredentialProviderProtocol(Protocol):
    """Protocol for providing credentials securely."""

    def get_openrouter_api_key(self) -> SecretStr | None: ...
