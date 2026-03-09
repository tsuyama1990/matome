from src.config import Settings, create_app_context


def test_settings_default() -> None:
    settings = Settings(mode="cli")
    assert settings.mode == "cli"
    assert settings.default_ai_model == "google/gemini-2.5-flash"


def test_app_context_creation() -> None:
    settings = Settings(mode="test")
    context = create_app_context(settings)
    assert context["mode"] == "test"
    assert context["settings"] is settings
    assert context["db"] is None
