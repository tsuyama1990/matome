from fastapi.testclient import TestClient

from src.domain_models.config import PipelineConfig
from src.main import create_app


def test_health_check() -> None:
    config = PipelineConfig()
    app = create_app(config)
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
