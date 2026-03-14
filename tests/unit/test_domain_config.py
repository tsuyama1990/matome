import pytest
from pydantic import ValidationError

from src.domain_models.config import AppConfig, ModelRoutingRules


def test_model_routing_rules_validation() -> None:
    # Valid model
    rules = ModelRoutingRules()
    assert rules.text_fast_model == "google/gemini-2.5-flash"

    # Empty string should fail because min_length=1
    with pytest.raises(ValidationError):
        ModelRoutingRules(text_fast_model="")

    # Extra fields should fail
    with pytest.raises(ValidationError) as excinfo:
        ModelRoutingRules(malicious_field="injection") # type: ignore[call-arg]
    assert "Extra inputs are not permitted" in str(excinfo.value)

def test_app_config_missing_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("TENANT_ID", raising=False)

    with pytest.raises(ValidationError) as excinfo:
        AppConfig(openrouter_api_key="sk-or-v1-mockmockmockmockmockmockmockmockmockmockmockmockmockmockmockmock", tenant_id="mock") # type: ignore[arg-type]

    # Needs OPENROUTER_API_KEY
    assert "validation error" in str(excinfo.value).lower()
    # Needs TENANT_ID


def test_app_config_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789")
    monkeypatch.setenv("TENANT_ID", "tenant-123")

    config = AppConfig(openrouter_api_key="sk-or-v1-abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789", tenant_id="tenant-123") # type: ignore[arg-type]

    assert config.tenant_id == "tenant-123"
    # SecretStr masks the representation
    assert str(config.openrouter_api_key) == "**********"
    assert config.openrouter_api_key.get_secret_value() == "sk-or-v1-abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"

def test_app_config_extra_forbid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789")
    monkeypatch.setenv("TENANT_ID", "tenant-123")
    monkeypatch.setenv("HACK_ME", "true")

    # Should not fail on extra environment variables, SettingsConfigDict parses env
    # But if initialized directly with kwargs, it should forbid extras
    with pytest.raises(ValidationError):
        AppConfig(openrouter_api_key="123", tenant_id="t1", extra_kwarg="should_fail") # type: ignore[call-arg, arg-type]
