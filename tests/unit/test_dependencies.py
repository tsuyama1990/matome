import pytest

from src.dependencies import ProductionDIContainer
from src.domain_models.config import CredentialConfig, PipelineConfig
from src.domain_models.node import DocumentNode
from src.domain_models.protocols import (
    CredentialProviderProtocol,
    DocumentRepository,
    NLPServiceProtocol,
    TransactionManager,
)
from src.domain_models.secure_string import SecureString


# Create mock classes to test initialization
class MockDocumentRepository(DocumentRepository):
    def save(self, node: DocumentNode) -> None:
        pass

    def get_by_id(self, node_id: str) -> DocumentNode | None:
        return None

    def list_all(self) -> list[DocumentNode]:
        return []


class MockTransactionManager(TransactionManager):
    def begin(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class MockNLPService(NLPServiceProtocol):
    def extract_entities(self, text: str) -> list[str]:
        return []

    def summarize(self, text: str) -> str:
        return ""


class MockCredentialProvider(CredentialProviderProtocol):
    def get_api_key(self) -> SecureString:
        return SecureString("mock_key")


def test_di_container_validation_failure() -> None:
    container = ProductionDIContainer()
    with pytest.raises(ValueError, match="pipeline_config is not initialized"):
        container.validate()


def test_di_container_initialization_success() -> None:
    container = ProductionDIContainer()

    pipeline_cfg = PipelineConfig()
    cred_cfg = CredentialConfig()
    doc_repo = MockDocumentRepository()
    tx_manager = MockTransactionManager()
    nlp_service = MockNLPService()
    cred_provider = MockCredentialProvider()

    container.initialize(
        pipeline_config=pipeline_cfg,
        credential_config=cred_cfg,
        document_repository=doc_repo,
        transaction_manager=tx_manager,
        nlp_service=nlp_service,
        credential_provider=cred_provider,
    )

    # Validation should succeed now
    container.validate()

    # Assert values
    assert container.pipeline_config == pipeline_cfg
    assert container.credential_config == cred_cfg
    assert container.document_repository == doc_repo
    assert container.transaction_manager == tx_manager
    assert container.nlp_service == nlp_service
    assert container.credential_provider == cred_provider
