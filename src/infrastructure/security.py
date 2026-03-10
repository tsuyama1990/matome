import os
import re

from llm_guard.input_scanners import PromptInjection
from llm_guard.input_scanners.prompt_injection import MatchType


class DefaultSecurityService:
    def validate_api_key(self, api_key: str) -> str:
        """Validates the structure and constraints of the BYOK API Key."""

        if not api_key:
            msg = "API Key cannot be empty."
            raise ValueError(msg)

        if len(api_key) < 30:
            msg = "API Key must be at least 30 characters long."
            raise ValueError(msg)

        if len(api_key) > 256:
            msg = "API Key must be less than 256 characters long."
            raise ValueError(msg)

        # Typical OpenRouter keys start with sk-or-v1- and contain mixed alphanumerics
        if not re.match(r"^sk-or-v1-[a-zA-Z0-9_-]+$", api_key):
            msg = "API Key format is invalid. It must start with 'sk-or-v1-' followed by alphanumeric characters."
            raise ValueError(msg)

        import math
        from collections import Counter

        # Calculate entropy to detect suspiciously simple keys like "sk-or-v1-1111111111111111111111"
        key_body = api_key.rsplit("sk-or-v1-", maxsplit=1)[-1]
        counts = Counter(key_body)
        entropy = -sum(
            count / len(key_body) * math.log2(count / len(key_body)) for count in counts.values()
        )
        if entropy < 3.5:
            msg = "API Key format is invalid. Key entropy is too low, indicating a potentially fake or compromised key."
            raise ValueError(msg)

        self._active_key_validation(api_key)

        return api_key

    def _active_key_validation(self, api_key: str) -> None:
        """Actively ping validation endpoint to confirm key validity and permissions securely."""
        if os.getenv("SKIP_ACTIVE_KEY_VALIDATION", "false").lower() == "true":
            return

        import requests

        validation_url = os.getenv(
            "OPENROUTER_AUTH_VALIDATION_URL", "https://openrouter.ai/api/v1/auth/key"
        )
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            # We strictly enforce short timeouts for configuration-time checks to prevent hanging boots
            response = requests.get(validation_url, headers=headers, timeout=5)
            if response.status_code in {401, 403}:
                msg = "API Key is unauthorized or expired according to the service."
                raise ValueError(msg)
            response.raise_for_status()
        except requests.RequestException as e:
            # Re-raise actively denied keys, otherwise log warnings to prevent hard-failing purely on network hiccups during boot
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Active API key validation network request failed, proceeding cautiously: {e}"
            )


class PromptInjectionScanner:
    def __init__(self, threshold: float | None = None, max_input_length: int = 50000) -> None:
        self.max_input_length = max_input_length

        env_threshold = os.getenv("PROMPT_INJECTION_THRESHOLD", "0.9")
        final_threshold = threshold if threshold is not None else float(env_threshold)

        if not (0.8 <= final_threshold <= 1.0):
            msg = f"Prompt injection threshold must be between 0.8 and 1.0. Got: {final_threshold}"
            from src.domain_models.exceptions import ConfigurationError

            raise ConfigurationError(msg)

        self._scanner = PromptInjection(threshold=final_threshold, match_type=MatchType.FULL)

    def _validate_basic_constraints(self, text: str) -> str:
        if len(text) > self.max_input_length:
            msg = "Input rejected due to excessive length."
            raise ValueError(msg)

        try:
            sanitized = text.encode("utf-8", "strict").decode("utf-8")
        except UnicodeError as e:
            msg = f"Input rejected due to invalid unicode encoding: {e}"
            raise ValueError(msg) from e

        if re.search(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", sanitized):
            msg = "Input rejected due to presence of unsafe control characters."
            raise ValueError(msg)

        import unicodedata

        for char in sanitized:
            cat = unicodedata.category(char)
            if cat in {"Cc", "Cf", "Cs", "Co", "Cn"} and char not in {"\n", "\r", "\t"}:
                msg = "Input rejected due to presence of malicious unicode character classes."
                raise ValueError(msg)

        return sanitized

    def sanitize(self, text: str | None) -> str:
        if not text:
            return ""

        if not isinstance(text, str):
            msg = "Input must be a string."
            raise TypeError(msg)

        sanitized = self._validate_basic_constraints(text)

        # Use llm-guard scanner to detect prompt injection
        def _scan_and_validate(text_to_scan: str) -> str:
            scanned_text, is_valid, risk_score = self._scanner.scan(text_to_scan)
            if not is_valid:
                err_msg = f"Input rejected due to suspected prompt injection semantics (risk: {risk_score})."
                raise ValueError(err_msg)
            return str(scanned_text)

        try:
            sanitized = _scan_and_validate(sanitized)
        except Exception as e:
            if isinstance(e, ValueError) and "semantics" in str(e):
                raise
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"llm-guard scanner failed: {e}. Falling back to regex scanning.")

        # Fallback layer just in case, catch any remaining raw commands
        injection_pattern = r"(?i)\b(ignore previous instructions|system prompt|you are a|disregard previous|forget what i said|ignore all|bypassing|developer mode|dan mode)\b"
        sanitized = re.sub(injection_pattern, "[REDACTED]", sanitized)

        # Escape markdown backticks to prevent breaking prompt formatting
        return sanitized.replace("```", "'''")
