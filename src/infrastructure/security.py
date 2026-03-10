import re

from llm_guard.input_scanners import PromptInjection
from llm_guard.input_scanners.prompt_injection import MatchType


class PromptInjectionScanner:
    def __init__(self) -> None:
        self._scanner = PromptInjection(threshold=0.5, match_type=MatchType.FULL)

    def sanitize(self, text: str | None) -> str:
        if not text:
            return ""

        # Basic length bound
        if len(text) > 50000:
            msg = "Input rejected due to excessive length."
            raise ValueError(msg)

        # Ensure valid unicode string and prevent encoding tricks strictly
        try:
            sanitized = text.encode("utf-8", "strict").decode("utf-8")
        except UnicodeError as e:
            msg = f"Input rejected due to invalid unicode encoding: {e}"
            raise ValueError(msg) from e

        # Strict validation of control characters instead of dropping
        if re.search(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", sanitized):
            msg = "Input rejected due to presence of unsafe control characters."
            raise ValueError(msg)

        # Use llm-guard scanner to detect prompt injection
        sanitized, is_valid, risk_score = self._scanner.scan(sanitized)
        if not is_valid:
            msg = (
                f"Input rejected due to suspected prompt injection semantics (risk: {risk_score})."
            )
            raise ValueError(msg)

        # Fallback layer just in case, catch any remaining raw commands
        injection_pattern = r"(?i)\b(ignore previous instructions|system prompt|you are a|disregard previous|forget what i said|ignore all|bypassing|developer mode|dan mode)\b"
        sanitized = re.sub(injection_pattern, "[REDACTED]", sanitized)

        # Escape markdown backticks to prevent breaking prompt formatting
        return sanitized.replace("```", "'''")
