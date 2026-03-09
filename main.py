import logging
import sys

from src.infrastructure import InMemoryDocumentRepository, MockAIService
from src.infrastructure.orchestrator import PipelineOrchestrator

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AppConfig:
    def __init__(self, mode: str = "cli") -> None:
        self.mode = mode

class Application:
    """Thin application controller responsible only for bootstrapping components."""
    def __init__(self, config: AppConfig, orchestrator: PipelineOrchestrator) -> None:
        self.config = config
        self.orchestrator = orchestrator

    def start(self) -> None:
        logger.info(f"Initializing matome application in {self.config.mode} mode...")
        self.orchestrator.run_pipeline()

def create_app(mode: str = "cli") -> Application:
    config = AppConfig(mode=mode)
    repo = InMemoryDocumentRepository()
    ai = MockAIService()
    orchestrator = PipelineOrchestrator(doc_repo=repo, ai_service=ai)
    return Application(config=config, orchestrator=orchestrator)

def main() -> None:
    try:
        app = create_app(mode="cli")
        app.start()
    except Exception:
        logger.exception("Application failed to start")
        sys.exit(1)

if __name__ == "__main__":
    main()
