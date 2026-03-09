import os

from src.config import Settings, create_app_context


def test_settings_default() -> None:
    os.environ["MODE"] = "cli"

    try:
        settings = Settings()
        assert settings.mode == "cli"
        assert settings.text_fast_model == "google/gemini-2.5-flash"
    finally:
        del os.environ["MODE"]


def test_app_context_creation() -> None:
    os.environ["MODE"] = "test"

    try:
        settings = Settings()
        context = create_app_context(settings)
        assert context["mode"] == "test"
        assert context["settings"] is settings
        assert context["db"] is None
    finally:
        del os.environ["MODE"]
