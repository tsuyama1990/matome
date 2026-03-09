import typing

import pytest
import requests


class MockResponse:
    def __init__(self, json_data: dict[str, typing.Any], status_code: int = 200) -> None:
        self.json_data = json_data
        self.status_code = status_code

    def json(self) -> dict[str, typing.Any]:
        return self.json_data


@pytest.fixture(autouse=True)
def mock_openrouter_api_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Globally mocks requests.get to intercept any openrouter.ai/api/v1/auth/key
    calls during test initializations, preventing slow or failing tests due to invalid dummy keys.
    """
    original_get = requests.get

    def mock_get(url: str, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if "openrouter.ai/api/v1/auth/key" in url:
            return MockResponse(json_data={"data": {"label": "mock_key"}}, status_code=200)
        return original_get(url, *args, **kwargs)

    monkeypatch.setattr(requests, "get", mock_get)
