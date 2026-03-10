import os
from typing import Any

from pydantic import SecretStr

from src.domain_models import (
    AIGatewayProtocol,
    AppConfig,
    CredentialProviderProtocol,
    DocumentRepository,
    UserRepository,
    VectorDBProtocol,
)


class EnvCredentialProvider(CredentialProviderProtocol):
    """
    Retrieves credentials strictly from environment variables.
    """

    def get_openrouter_api_key(self) -> SecretStr | None:
        key = os.environ.get("OPENROUTER_API_KEY")
        if key:
            return SecretStr(key)
        return None


class DIContainer:
    """
    Centralized Dependency Injection container for the application.
    """

    def __init__(self, env_overrides: dict[str, Any] | None = None) -> None:
        """
        Initializes the container and builds the validated AppConfig.
        """
        self.env_overrides = env_overrides or {}

        # Filter env_overrides to pre-filter env vars and ensure extra="forbid" checks run correctly
        filtered_env = {k: v for k, v in self.env_overrides.items() if v is not None}

        # AppConfig is a BaseSettings model and will automatically parse `APP_ENV`,
        # `PIPELINE__MAX_CHUNK_SIZE` and other nested variables correctly.
        self.config = AppConfig(**filtered_env)

        self.credential_provider: CredentialProviderProtocol = EnvCredentialProvider()

        # These will be populated with concrete implementations in later cycles
        self.document_repo: DocumentRepository | None = None
        self.user_repo: UserRepository | None = None
        self.vector_db: VectorDBProtocol | None = None
        self.ai_gateway: AIGatewayProtocol | None = None

    def get_config(self) -> AppConfig:
        return self.config

    def get_credential_provider(self) -> CredentialProviderProtocol:
        return self.credential_provider
