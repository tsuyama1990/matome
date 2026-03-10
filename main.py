import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.di_container import DIContainer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize the DI Container
    container = DIContainer()
    app.state.container = container
    yield


app = FastAPI(
    title="matome API",
    description="Interactive summarization for very long texts",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def root_endpoint() -> dict[str, str]:
    """Preserves the original legacy behavior via API."""
    return {"message": "Hello from matome!"}


def main() -> None:
    # Print the legacy message if run directly as a script without args to start the server
    print("Hello from matome!")  # noqa: T201

    # We still allow starting the server if run directly (e.g. `python main.py server`)
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
