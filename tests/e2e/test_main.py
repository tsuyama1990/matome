from fastapi.testclient import TestClient

from main import app


def test_main_root() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from matome!"}


def test_main_startup_state() -> None:
    # Use the context manager to trigger lifespan events
    with TestClient(app) as client:
        # FastAPI's test client automatically calls the lifespan events
        response = client.get("/")
        assert response.status_code == 200

        # We can also verify that the container is placed into the app state
        assert hasattr(app.state, "container")
        container = app.state.container
        assert container is not None
        assert container.get_config() is not None
