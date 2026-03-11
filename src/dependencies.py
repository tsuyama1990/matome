from src.domain_models import (
    CredentialConfig,
    CredentialProviderProtocol,
    DocumentRepository,
    NLPServiceProtocol,
    PipelineConfig,
    TransactionManager,
)


class ProductionDIContainer:
    def __init__(self) -> None:
        self.pipeline_config: PipelineConfig | None = None
        self.credential_config: CredentialConfig | None = None
        self.document_repository: DocumentRepository | None = None
        self.transaction_manager: TransactionManager | None = None
        self.nlp_service: NLPServiceProtocol | None = None
        self.credential_provider: CredentialProviderProtocol | None = None

    def validate(self) -> None:
        """Strict validation check to ensure no uninitialized dependencies."""
        # For Cycle 01, we only strictly enforce the initialization of configs
        if self.pipeline_config is None:
            msg = "pipeline_config is not initialized"
            raise ValueError(msg)
        if self.credential_config is None:
            msg = "credential_config is not initialized"
            raise ValueError(msg)

        # NOTE: External infrastructural protocols will be enforced in Cycle 02+
