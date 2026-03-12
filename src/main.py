from fastapi import FastAPI

from src.domain_models.config import PipelineConfig


def create_app(config: PipelineConfig) -> FastAPI:
    app = FastAPI(title="matome")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "healthy"}

    return app

def main() -> None:
    pass

if __name__ == "__main__":
    main()
