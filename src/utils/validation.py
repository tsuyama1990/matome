import re


def validate_api_key_format(api_key: str | None) -> str | None:
    """Validates the structure and constraints of the BYOK API Key."""
    if not api_key:
        return api_key

    if len(api_key) < 10:
        msg = "API Key must be at least 10 characters long."
        raise ValueError(msg)

    if not re.match(r"^[a-zA-Z0-9_-]+$", api_key):
        msg = "API Key format is invalid. It must contain only alphanumeric characters, dashes, or underscores."
        raise ValueError(msg)

    return api_key
