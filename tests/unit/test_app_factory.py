import os

from src.config import Settings, create_app_context


def test_settings_default() -> None:
    os.environ["MODE"] = "cli"
    os.environ["DEFAULT_AI_MODEL"] = "google/gemini-2.5-flash"
    os.environ["DEFAULT_ROOT_DOC_ID"] = "root_doc_1"

    settings = Settings()
    assert settings.mode == "cli"
    assert settings.default_ai_model == "google/gemini-2.5-flash"


def test_app_context_creation() -> None:
    os.environ["MODE"] = "test"
    os.environ["DEFAULT_AI_MODEL"] = "google/gemini-2.5-flash"
    os.environ["DEFAULT_ROOT_DOC_ID"] = "root_doc_1"

    settings = Settings()
    context = create_app_context(settings)
    assert context["mode"] == "test"
    assert context["settings"] is settings
    assert context["db"] is None
