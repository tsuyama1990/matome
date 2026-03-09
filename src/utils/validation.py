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

    return api_key
