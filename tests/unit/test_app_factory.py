from src import Settings, create_app_context


def test_settings_default() -> None:
    settings = Settings()
    assert settings.get("missing") is None
    assert settings.get("missing", "default") == "default"

def test_app_context_creation() -> None:
    settings = Settings({"mode": "test"})
    context = create_app_context(settings)
    assert context["mode"] == "test"
    assert context["settings"] is settings
    assert context["db"] is None
