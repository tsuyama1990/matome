import logging
import os
import sys

from src.application.ai import DefaultAIService
from src.config import Settings
from src.domain_models.services import DocumentFactory
from src.infrastructure import InMemoryDocumentRepository
from src.infrastructure.orchestrator import PipelineOrchestrator

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Application:
    """Thin application controller responsible only for bootstrapping components."""

    def __init__(self, settings: Settings, orchestrator: PipelineOrchestrator) -> None:
        self.settings = settings
        self.orchestrator = orchestrator

    def start(self) -> None:
        logger.info(f"Initializing matome application in {self.settings.mode} mode...")
        # Provide sample content directly instead of hardcoding in settings
        sample_content = "This is a very long business manual about strategy."
        self.orchestrator.run_pipeline(
            root_doc_id=self.settings.default_root_doc_id, content=sample_content
        )


def create_app(mode: str = "cli") -> Application:
    os.environ["MODE"] = mode
    os.environ["DEFAULT_AI_MODEL"] = "google/gemini-2.5-flash"
    os.environ["DEFAULT_ROOT_DOC_ID"] = "root_doc_1"

    settings = Settings()
    repo = InMemoryDocumentRepository()
    ai = DefaultAIService()
    factory = DocumentFactory()
    orchestrator = PipelineOrchestrator(doc_repo=repo, ai_service=ai, doc_factory=factory)
    return Application(settings=settings, orchestrator=orchestrator)


def main() -> None:
    try:
        app = create_app(mode="cli")
        app.start()
    except Exception:
        logger.exception("Application failed to start")
        sys.exit(1)


if __name__ == "__main__":
    main()
