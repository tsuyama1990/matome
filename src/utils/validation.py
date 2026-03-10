import re


def validate_api_key_format(api_key: str | None) -> str | None:
    """Validates the structure and constraints of the BYOK API Key."""
    if not api_key:
        msg = "API Key cannot be empty."
        raise ValueError(msg)

    if len(api_key) < 20 or len(api_key) > 256:
        msg = "API Key must be between 20 and 256 characters long."
        raise ValueError(msg)

    # Allow generic API keys with alphanumeric and safe symbols for provider-agnostic support
    if not re.match(r"^[a-zA-Z0-9_.-]+$", api_key):
        msg = "API Key format is invalid. It must contain only alphanumeric characters, underscores, dots, or hyphens."
        raise ValueError(msg)

    import math
    from collections import Counter

    counts = Counter(api_key)
    entropy = -sum(
        count / len(api_key) * math.log2(count / len(api_key)) for count in counts.values()
    )
    if entropy < 3.5:
        msg = "API Key format is invalid. Key entropy is too low, indicating a potentially fake or compromised key."
        raise ValueError(msg)

    return api_key


def validate_ai_model(value: str) -> str:
    """Validates an AI model against the allowed whitelist."""
    import os

    allowed_env = os.getenv("ALLOWED_AI_MODELS")
    if not allowed_env:
        msg = "ALLOWED_AI_MODELS environment variable must be explicitly configured."
        raise ValueError(msg)

    allowed_whitelist = {m.strip() for m in allowed_env.split(",") if m.strip()}

    if value.strip() not in allowed_whitelist:
        msg = f"Untrusted AI Model configured: {value}. Only verified models ({allowed_env}) are allowed."
        raise ValueError(msg)
    return value
