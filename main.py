import logging
import sys
from typing import Any

from src.config import ModeConfig, Settings
from src.domain_models.exceptions import ConfigurationError
from src.domain_models.manifest import PipelineContext
from src.infrastructure.orchestrator import (
    PipelineConfig,
    PipelineDependencies,
    PipelineOrchestrator,
)

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Application:
    """Thin application controller responsible only for executing application logic."""

    def __init__(
        self, settings: Settings, mode_config: ModeConfig, orchestrator: PipelineOrchestrator
    ) -> None:
        self.settings = settings
        self.mode_config = mode_config
        self.orchestrator = orchestrator

    def start(self, context: PipelineContext) -> None:
        logger.info(f"Initializing matome application in {self.mode_config.mode} mode...")
        self.orchestrator.run_pipeline(context)


def build_app(
    settings: Settings, mode_config: ModeConfig, deps: PipelineDependencies, config: PipelineConfig
) -> Application:
    """Factory function for bootstrapping components and dependency injection, detached from state."""
    orchestrator = PipelineOrchestrator(dependencies=deps, config=config)
    return Application(settings=settings, mode_config=mode_config, orchestrator=orchestrator)


def get_di_container(settings: Settings) -> Any:
    from src.infrastructure.container import ProductionDIContainer

    return ProductionDIContainer(settings)


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="matome CLI Application")
    parser.add_argument("--file", type=str, help="Path to the document to process", required=True)
    args = parser.parse_args()

    import os

    try:
        try:
            mode = os.getenv("MODE", "cli")
            if mode not in ["cli", "production", "test"]:
                msg = f"Invalid mode: {mode}. Must be one of 'cli', 'production', 'test'."
                raise ValueError(msg)

            filtered_env = {
                k.lower(): v for k, v in os.environ.items() if k.lower() in Settings.model_fields
            }
            settings = Settings(**filtered_env)  # type: ignore[arg-type]
            mode_config = ModeConfig(mode=mode)

            container = get_di_container(settings)
            deps, config = container.get_dependencies()
            app = build_app(settings, mode_config, deps, config)
        except ConfigurationError:
            logger.exception("Configuration Error")
            sys.exit(1)

        allowed_dir = Path(app.settings.allowed_base_dir).resolve()
        file_path = Path(args.file).resolve()

        if not file_path.exists():
            logger.error(f"Failed to execute pipeline: File not found -> {file_path}")
            sys.exit(1)
        if not file_path.is_file():
            logger.error(f"Failed to execute pipeline: Path is not a valid file -> {file_path}")
            sys.exit(1)

        # Prevent directory traversal by checking against configured allowed directory
        real_file_path = str(Path(os.path.realpath(file_path)).resolve())
        real_allowed_dir = str(Path(os.path.realpath(allowed_dir)).resolve())
        if not real_file_path.startswith(real_allowed_dir):
            logger.error("Security Error: Access denied to the requested file.")
            sys.exit(1)

        if file_path.stat().st_size > app.settings.max_file_size:
            logger.error(
                f"Security Error: File exceeds maximum allowed size of {app.settings.max_file_size} bytes -> {file_path}"
            )
            sys.exit(1)

        # Pass the file path to the pipeline for chunked streaming to prevent OOM
        context = PipelineContext(
            root_doc_id=app.settings.default_root_doc_id, file_path=str(file_path)
        )
        app.start(context)
    except ValueError:
        logger.exception("Configuration or validation error during startup")
        sys.exit(1)
    except RuntimeError:
        logger.exception("Pipeline execution halted due to a runtime error")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unexpected critical failure occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
