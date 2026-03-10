import re


def validate_api_key_format(api_key: str | None) -> str | None:
    """Validates the structure and constraints of the BYOK API Key."""
    if not api_key:
        msg = "API Key cannot be empty."
        raise ValueError(msg)

    if len(api_key) < 30 or len(api_key) > 256:
        msg = "API Key must be between 30 and 256 characters long."
        raise ValueError(msg)

    # Typical OpenRouter keys start with sk-or-v1- and contain mixed alphanumerics
    if not re.match(r"^sk-or-v1-[a-zA-Z0-9_-]+$", api_key):
        msg = "API Key format is invalid. It must start with 'sk-or-v1-' followed by alphanumeric characters."
        raise ValueError(msg)

    import math
    from collections import Counter
    key_body = api_key.rsplit("sk-or-v1-", maxsplit=1)[-1]
    counts = Counter(key_body)
    entropy = -sum(count/len(key_body) * math.log2(count/len(key_body)) for count in counts.values())
    if entropy < 3.5:
         msg = "API Key format is invalid. Key entropy is too low, indicating a potentially fake or compromised key."
         raise ValueError(msg)

    return api_key

def validate_ai_model(value: str) -> str:
    """Validates an AI model against the allowed whitelist."""
    import os

    allowed_env = os.getenv(
        "ALLOWED_AI_MODELS", "google/gemini-2.5-flash,deepseek/deepseek-reasoner,openai/gpt-4o"
    )
    allowed_whitelist = {m.strip() for m in allowed_env.split(",") if m.strip()}

    if value.strip() not in allowed_whitelist:
        msg = f"Untrusted AI Model configured: {value}. Only verified models ({allowed_env}) are allowed."
        raise ValueError(msg)
    return value
