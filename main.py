import logging
import sys

from pydantic import ValidationError

from src.config.security import SecurityService
from src.config.settings import AppConfig, ModelConfig
from src.interfaces.dependencies import DIContainer

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def init_di_container(app_config: AppConfig, model_config: ModelConfig) -> DIContainer:
    """Initializes the dependency injection container."""
    container = DIContainer()

    # Register configs and core services
    container.register(AppConfig, lambda: app_config)
    container.register(ModelConfig, lambda: model_config)

    def security_service_factory() -> SecurityService:
        return SecurityService()

    container.register(SecurityService, security_service_factory)

    # Example placeholder resolution for future LLM and VectorStore integration
    # These will be explicitly wired when the actual infrastructure implementation occurs.

    return container


def main() -> None:
    """Application entrypoint. Initializes services and orchestrates workflow."""
    logger.info("Starting matome application...")

    try:
        app_config = AppConfig()  # type: ignore[call-arg]
        model_config = ModelConfig()  # type: ignore[call-arg]
        logger.info(f"Loaded configuration for environment: {app_config.environment}")
    except ValidationError:
        logger.exception("Failed to load configurations. Missing environment variables.")
        sys.exit(1)

    container = init_di_container(app_config, model_config)

    # Securely instantiate security service to ensure the encryption keys are valid
    try:
        container.resolve(SecurityService)
        logger.info("Security service initialized securely.")
    except Exception:
        logger.exception("Security service initialization failed.")
        sys.exit(1)

    # Note: In future cycles, the LangGraph processing workflow
    # (Document Ingestion -> RAPTOR -> UI) will be triggered from here.
    logger.info("Application initialized successfully. Awaiting tasks.")


if __name__ == "__main__":
    main()
