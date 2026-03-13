import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.interfaces.api_router import router
from src.interfaces.dependencies import DIContainer, bootstrap_application_services

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    logger.info("Initializing DI Container and Bootstrapping Services.")
    container = DIContainer()
    # In a real setup, we would ensure required environment variables are set.
    # Here, bootstrap_application_services will check what it needs and degrade otherwise.
    bootstrap_application_services(container)
    app.state.container = container
    yield
    # Shutdown
    logger.info("Shutting down application.")

app = FastAPI(title="matome", lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # noqa: S104
