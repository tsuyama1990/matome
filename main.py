import logging
import sys

from src.domain_models import DocumentNode, NodeMetadata, NodeStatus
from src.infrastructure import InMemoryDocumentRepository
from src.interfaces.protocols import AIMockService, DocumentRepository

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockAIService:
    def generate_summary(self, content: str) -> str:
        return f"CoD Summary of: {content[:20]}..."

    def generate_question(self, node: DocumentNode) -> str:
        return f"What is the key point of {node.title}?"

class AppConfig:
    def __init__(self, mode: str = "cli") -> None:
        self.mode = mode

class Application:
    def __init__(self, config: AppConfig, doc_repo: DocumentRepository, ai_service: AIMockService) -> None:
        self.config = config
        self.doc_repo = doc_repo
        self.ai_service = ai_service

    def start(self) -> None:
        logger.info(f"Initializing matome application in {self.config.mode} mode...")
        self.orchestrate_pipeline()

    def orchestrate_pipeline(self) -> None:
        logger.info("Starting document ingestion and analysis pipeline...")

        # 1. Ingestion Stage
        content = "This is a very long business manual about strategy."
        logger.info("Ingesting document...")

        root_node = DocumentNode(
            id="root_doc_1",
            parent_id=None,
            title="Business Manual",
            summary=self.ai_service.generate_summary(content),
            content=content,
            status=NodeStatus.LOCKED,
            metadata=NodeMetadata(category="business", author="System", source="upload", time_axis=None)
        )
        self.doc_repo.save_node(root_node)

        # 2. AI Processing Stage (Mocked)
        logger.info(f"Generating learning loop for node {root_node.id}...")
        question = self.ai_service.generate_question(root_node)
        logger.info(f"AI Question: {question}")

        # 3. UI Initialization
        logger.info("UI initialized. Awaiting user interaction...")

        sys.stdout.write("Pipeline execution completed successfully.\n")

def create_app(mode: str = "cli") -> Application:
    config = AppConfig(mode=mode)
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    return Application(config=config, doc_repo=repo, ai_service=ai)

def main() -> None:
    try:
        app = create_app(mode="cli")
        app.start()
    except Exception:
        logger.exception("Application failed to start")
        sys.exit(1)

if __name__ == "__main__":
    main()
