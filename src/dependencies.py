from src.domain_models.config import CredentialConfig, PipelineConfig
from src.domain_models.protocols import (
    CredentialProviderProtocol,
    DocumentRepository,
    NLPServiceProtocol,
    TransactionManager,
)


class ProductionDIContainer:
    """Dependency Injection Container for the production environment."""

    def __init__(self) -> None:
        self.pipeline_config: PipelineConfig | None = None
        self.credential_config: CredentialConfig | None = None

        self.document_repository: DocumentRepository | None = None
        self.transaction_manager: TransactionManager | None = None
        self.nlp_service: NLPServiceProtocol | None = None
        self.credential_provider: CredentialProviderProtocol | None = None

    def initialize(
        self,
        pipeline_config: PipelineConfig,
        credential_config: CredentialConfig,
        document_repository: DocumentRepository,
        transaction_manager: TransactionManager,
        nlp_service: NLPServiceProtocol,
        credential_provider: CredentialProviderProtocol,
    ) -> None:
        """Initialize and validate dependencies."""
        self.pipeline_config = pipeline_config
        self.credential_config = credential_config
        self.document_repository = document_repository
        self.transaction_manager = transaction_manager
        self.nlp_service = nlp_service
        self.credential_provider = credential_provider
        self.validate()

    def validate(self) -> None:
        if self.pipeline_config is None:
            msg = "pipeline_config is not initialized"
            raise ValueError(msg)
        if self.credential_config is None:
            msg = "credential_config is not initialized"
            raise ValueError(msg)
        if self.document_repository is None:
            msg = "document_repository is not initialized"
            raise ValueError(msg)
        if self.transaction_manager is None:
            msg = "transaction_manager is not initialized"
            raise ValueError(msg)
        if self.nlp_service is None:
            msg = "nlp_service is not initialized"
            raise ValueError(msg)
        if self.credential_provider is None:
            msg = "credential_provider is not initialized"
            raise ValueError(msg)


container = ProductionDIContainer()
