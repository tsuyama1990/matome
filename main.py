import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.dependencies import ProductionDIContainer
from src.domain_models import CredentialConfig, PipelineConfig


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize the centralized Dependency Injection Container safely
    container = ProductionDIContainer()

    # Load configuration securely from environment/defaults
    container.pipeline_config = PipelineConfig()
    container.credential_config = CredentialConfig()

    # Validate container completeness for Cycle 01
    container.validate()

    # NOTE: Actual components will be initialized and injected here in future cycles
    app.state.container = container

    sys.stdout.write("Hello from matome!\n")
    yield
    # Safely teardown resources
    app.state.container = None


app = FastAPI(lifespan=lifespan)


def main() -> None:
    sys.stdout.write("Hello from matome!\n")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
