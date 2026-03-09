import logging
import sys

from src.application.ai import DefaultAIService
from src.config import Settings
from src.domain_models.manifest import PipelineContext
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
        context = PipelineContext(
            root_doc_id=self.settings.default_root_doc_id, content=self.settings.default_sample_content
        )
        self.orchestrator.run_pipeline(context)


def create_app(mode: str = "cli") -> Application:
    # Use settings passed directly or initialized from the environment
    settings = Settings(mode=mode)
    repo = InMemoryDocumentRepository()

    api_key_str = (
        settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else None
    )
    ai = DefaultAIService(api_key=api_key_str, model=settings.text_fast_model)
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
