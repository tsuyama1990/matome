with open("tests/unit/test_domain_config.py") as f:
    content = f.read()

content = content.replace(
    'config = AppConfig(openrouter_api_key="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", tenant_id="mock") # type: ignore[arg-type]',
    "config = AppConfig()",
)

content = content.replace(
    'with pytest.raises(ValidationError) as excinfo:\n        AppConfig(openrouter_api_key="sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", tenant_id="mock") # type: ignore[arg-type]',
    "with pytest.raises(ValidationError) as excinfo:\n        AppConfig()",
)

content = content.replace("AppConfig() # type: ignore[call-arg]", "AppConfig()")

with open("tests/unit/test_domain_config.py", "w") as f:
    f.write(content)
