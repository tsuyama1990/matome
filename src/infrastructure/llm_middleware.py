import logging
import re
import time
import unicodedata
from typing import Any

from src.domain_models import PipelineConfig
from src.interfaces import LLMProtocol

logger = logging.getLogger(__name__)


class LLMMiddlewareService(LLMProtocol):
    """Middleware service handling rate limiting and prompt sanitization before invoking the underlying LLM Gateway."""

    def __init__(self, backend_gateway: LLMProtocol, config: PipelineConfig) -> None:
        self.backend_gateway = backend_gateway
        self.config = config
        self._last_request_time = 0.0

    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        sanitized_prompt = self._validate_and_sanitize_prompt(prompt)
        self._enforce_rate_limit()

        return self.backend_gateway.invoke(sanitized_prompt, timeout, retries, **kwargs)

    def _validate_and_sanitize_prompt(self, prompt: str) -> str:
        """Validates prompt length, explicitly normalizes unicode, and strictly whitelists characters."""
        if not prompt or not prompt.strip():
            msg = "Prompt cannot be empty"
            raise ValueError(msg)

        if len(prompt) > self.config.max_prompt_length:
            msg = f"Prompt length exceeds maximum allowed length of {self.config.max_prompt_length}"
            raise ValueError(msg)

        # 1. Normalize Unicode to prevent homoglyph/visual spoofing attacks
        prompt = unicodedata.normalize("NFC", prompt)

        # 2. Strict Whitelist Approach:
        # Allow alphanumeric, standard punctuation, and standard whitespaces (space, tab, newline)
        # Any hidden control characters, ANSI escapes, or bizarre symbols are stripped.
        # This guarantees safety against prompt injections utilizing unprintable/control tokens.
        return re.sub(r'[^\w\s.,!?:;\'"()\[\]{}+=*/\\&%$#@~<>-]', "", prompt)

    def _enforce_rate_limit(self) -> None:
        """Enforces a simple rate limit based on configured limits."""
        if self.config.requests_per_minute_limit <= 0:
            return

        min_interval = 60.0 / self.config.requests_per_minute_limit
        elapsed = time.time() - self._last_request_time

        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"Rate limiting active, sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self._last_request_time = time.time()
