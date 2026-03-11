import sys
from collections.abc import Generator
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from main import app, main


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client


def test_main_terminal_output(monkeypatch: pytest.MonkeyPatch) -> None:
    # Capture sys.stdout
    captured_output = StringIO()
    monkeypatch.setattr(sys, "stdout", captured_output)

    # Call main
    main()

    # Assert legacy terminal output remains unchanged
    assert captured_output.getvalue() == "Hello from matome!\n"


def test_fastapi_lifespan_di_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    # Capture sys.stdout to prevent noise and verify startup output BEFORE launching TestClient
    captured_output = StringIO()
    monkeypatch.setattr(sys, "stdout", captured_output)

    # Send a request to an arbitrary endpoint (even if 404) to trigger the lifespan
    with TestClient(app) as test_client:
        response = test_client.get("/")
        assert response.status_code == 404

        # Assert lifespan printed the expected output
        assert "Hello from matome!\n" in captured_output.getvalue()

        # The container should be attached to app.state
        assert hasattr(app.state, "container")
        from src.dependencies import ProductionDIContainer
        assert isinstance(app.state.container, ProductionDIContainer)
