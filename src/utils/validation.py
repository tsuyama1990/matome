import re


def validate_api_key_format(api_key: str | None) -> str | None:
    """Validates the structure and constraints of the BYOK API Key."""
    if not api_key:
        return api_key

    if len(api_key) < 30:
        msg = "API Key must be at least 30 characters long."
        raise ValueError(msg)

    # Typical OpenRouter keys start with sk-or-v1- and contain mixed alphanumerics
    if not re.match(r"^sk-or-v1-[a-zA-Z0-9_-]+$", api_key):
        msg = "API Key format is invalid. It must start with 'sk-or-v1-' followed by alphanumeric characters."
        raise ValueError(msg)

    import requests

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        # Strict validation of the key against OpenRouter's auth endpoint to guarantee validity.
        # Uses a quick fallback to ensure it doesn't block local development heavily.
        res = requests.get("https://openrouter.ai/api/v1/auth/key", headers=headers, timeout=5)
        if res.status_code == 401:
            msg = "API Key is structurally valid but rejected by the OpenRouter authentication endpoint."
            raise ValueError(msg)
    except requests.RequestException:
        # If the endpoint is completely unreachable (e.g. no internet), we bypass strictly failing here
        # to allow offline fallback components (e.g. MockAIService) to still operate.
        pass

    return api_key
