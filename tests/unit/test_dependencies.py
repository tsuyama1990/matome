import pytest

from src.dependencies import ProductionDIContainer
from src.domain_models import (
    CredentialConfig,
    CredentialProviderProtocol,
    DocumentRepository,
    NLPServiceProtocol,
    PipelineConfig,
    TransactionManager,
)
from src.domain_models.node import DocumentNode
from src.domain_models.secure_string import SecureString


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

    # Validation should fail because no dependencies are initialized
    with pytest.raises(ValueError, match="pipeline_config is not initialized"):
        container.validate()


def test_di_container_validation_success() -> None:
    container = ProductionDIContainer()

    container.pipeline_config = PipelineConfig()
    container.credential_config = CredentialConfig()

    # For Cycle 01 testing, we only check configs are required.
    # External protocols are deferred to cycle 02.

    # Should not raise any ValueError
    container.validate()

    # Verify mapping explicitly
    assert container.pipeline_config is not None
    assert container.credential_config is not None
