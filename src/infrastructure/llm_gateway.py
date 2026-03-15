import ipaddress
import logging
import os
import socket
from typing import Any

import httpx

from src.config.settings import ModelConfig

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM operations."""


class OpenRouterGateway:
    """Gateway for OpenRouter API."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

        self._validate_environment()
        self._validate_allowed_hosts()
        self._validate_api_url()
        self._validate_models()

        # Security: strictly validate the encrypted API key before assigning it
        encrypted_key = os.environ.get("OPENROUTER_API_KEY_ENCRYPTED")
        if not encrypted_key or not encrypted_key.strip():
            msg = "OPENROUTER_API_KEY_ENCRYPTED environment variable is missing or empty."
            raise ValueError(msg)

        # Format validation for Fernet encrypted token:
        # Fernet tokens start with 'gAAAAA' and are URL-safe base64.
        import re

        if not re.match(self._config.fernet_token_pattern, encrypted_key):
            msg = "OPENROUTER_API_KEY_ENCRYPTED format is invalid. Expected a valid Fernet token."
            raise ValueError(msg)

        self._encrypted_api_key = encrypted_key

    def _validate_environment(self) -> None:
        # Verify ENCRYPTION_KEY exists FIRST
        enc_key = os.environ.get("ENCRYPTION_KEY")
        if not enc_key or len(enc_key.strip()) < 44:
            msg = "ENCRYPTION_KEY environment variable is missing or invalid format."
            raise ValueError(msg)

    def _validate_allowed_hosts(self) -> None:
        # Validate allowed_hosts first for SSRF protection
        if not self._config.allowed_hosts or not isinstance(self._config.allowed_hosts, list):
            msg = "Invalid ModelConfig: allowed_hosts is required and must be a non-empty list."
            raise ValueError(msg)

        import re

        domain_regex = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\.?$"
        )
        for host in self._config.allowed_hosts:
            if not domain_regex.match(host) and host != "localhost":
                msg = f"Invalid domain name in allowed_hosts: {host}"
                raise ValueError(msg)

    def _validate_api_url(self) -> None:
        # Validate openrouter_api_url is HTTPS and matches allowed hosts
        api_url = str(self._config.openrouter_api_url)
        if not api_url or not api_url.startswith("https://"):
            msg = "Invalid ModelConfig: openrouter_api_url must be a valid HTTPS URL."
            raise ValueError(msg)

        from urllib.parse import urlparse

        parsed_url = urlparse(api_url)
        host_lower = parsed_url.hostname.lower() if parsed_url.hostname else ""
        is_allowed = any(
            host_lower == allowed.lower() or host_lower.endswith(f".{allowed.lower()}")
            for allowed in self._config.allowed_hosts
        )
        if not is_allowed:
            msg = f"API URL host {host_lower} is not in allowed_hosts."
            raise ValueError(msg)

        try:
            addr_info = socket.getaddrinfo(host_lower, 443, socket.AF_INET, socket.SOCK_STREAM)
            ip_str: str = str(addr_info[0][4][0])
            ip_obj = ipaddress.ip_address(ip_str)
            if ip_obj.is_private or ip_obj.is_loopback:
                msg = "SSRF Attempt: Disallowed private or loopback IP."
                raise ValueError(msg)
        except socket.gaierror as e:
            msg = f"DNS resolution failed for {host_lower}"
            raise ValueError(msg) from e

    def _validate_models(self) -> None:
        # Validate models against an allowed whitelist format to prevent arbitrary model injection
        import re

        model_pattern = re.compile(r"^[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-_.]+$")

        models_to_check = {
            "text_reasoning_model": self._config.text_reasoning_model,
            "text_fast_model": self._config.text_fast_model,
            "multimodal_model": self._config.multimodal_model,
        }

        for field_name, model_val in models_to_check.items():
            if not model_val or not isinstance(model_val, str) or not model_val.strip():
                msg = f"Invalid ModelConfig: {field_name} must be a non-empty string."
                raise ValueError(msg)
            if not model_pattern.match(model_val):
                msg = f"Invalid ModelConfig: {field_name} '{model_val}' does not match expected model format."
                raise ValueError(msg)

        if self._config.llm_timeout <= 0 or self._config.llm_timeout > 120.0:
            msg = "Invalid ModelConfig: timeout must be between 0 and 120 seconds."
            raise ValueError(msg)

        # Security: strictly validate the encrypted API key before assigning it
        encrypted_key = os.environ.get("OPENROUTER_API_KEY_ENCRYPTED")
        if not encrypted_key or not encrypted_key.strip():
            msg = "OPENROUTER_API_KEY_ENCRYPTED environment variable is missing or empty."
            raise ValueError(msg)

        # Format validation for Fernet encrypted token:
        # Fernet tokens start with 'gAAAAA' and are URL-safe base64.
        import re

        if not re.match(self._config.fernet_token_pattern, encrypted_key):
            msg = "OPENROUTER_API_KEY_ENCRYPTED format is invalid. Expected a valid Fernet token."
            raise ValueError(msg)

        self._encrypted_api_key = encrypted_key

    async def __aenter__(self) -> "OpenRouterGateway":
        from src.infrastructure.network import SecureAsyncHTTPTransport

        transport = SecureAsyncHTTPTransport(allowed_hosts=self._config.allowed_hosts)
        # Using verify=True explicitly to ensure strict SSL verification as requested
        self._client = httpx.AsyncClient(
            timeout=self._config.llm_timeout, transport=transport, verify=True
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitizes input prompt string using robust security validation."""
        if not prompt:
            msg = "Prompt cannot be empty."
            raise ValueError(msg)

        if len(prompt) > self._config.max_prompt_length:
            msg = "Prompt exceeds maximum allowed length."
            raise ValueError(msg)

        # Basic token approximation. Most models max out around 128k - 200k tokens. We use 25000 max.
        approx_tokens = len(prompt) / 4
        if approx_tokens > self._config.max_prompt_tokens:
            msg = "Prompt exceeds approximate token limits."
            raise ValueError(msg)

        import re

        # Block null bytes and other dangerous control characters strictly across all planes
        if re.search(r"[\x00-\x1F\x7F-\x9F]", prompt):
            msg = "Prompt contains forbidden control characters."
            raise ValueError(msg)

        # Block common prompt injection phrases using comprehensive patterns

        prompt_lower = prompt.lower()

        # Advanced regex patterns to catch sophisticated injections including obfuscation
        injection_patterns = [
            r"ignore\s+(?:all\s+)?(?:previous\s+)?(?:instructions|directions)",
            r"forget\s+(?:all\s+)?(?:previous\s+)?(?:instructions|directions)",
            r"system\s+prompt",
            r"you\s+are\s+now\s+a\s+",
            r"bypassing\s+filters",
            r"jailbreak",
            r"DAN\s+mode",
            r"do\s+anything\s+now",
        ]

        for pattern in injection_patterns:
            if re.search(pattern, prompt_lower):
                msg = "Prompt contains disallowed injection patterns."
                raise ValueError(msg)

        # Allow formatting, standard punctuation, code blocks but block terminal escapes like \x1b
        # Also block characters often used for prompt smuggling/escaping
        if "\x1b" in prompt or "\u001b" in prompt or "\u200b" in prompt:
            msg = "Prompt contains terminal escape or zero-width sequences."
            raise ValueError(msg)

        # Remove control characters using a safer whitelist of valid characters instead of strict regex,
        # allowing all unicode printables, \n, \r, \t
        sanitized_prompt = "".join(
            char for char in prompt if char.isprintable() or char in "\n\r\t"
        )

        if not sanitized_prompt.strip():
            msg = "Prompt is effectively empty after sanitization."
            raise ValueError(msg)

        return sanitized_prompt

    async def generate(self, prompt: str) -> str:
        """Generates text from a prompt."""
        return await self.generate_text(prompt, self._config.text_fast_model)

    async def generate_text(self, prompt: str, model: str) -> str:
        """Generates text from a prompt for a specific model."""
        import re

        from src.config.security import SecurityService

        if self._client is None:
            msg = "Client not initialized. Use async context manager."
            raise RuntimeError(msg)

        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            msg = "Prompt cannot be empty or non-string."
            raise ValueError(msg)

        sanitized_prompt = self._sanitize_prompt(prompt)

        security_service = SecurityService()
        with security_service.get_decrypted_key(self._encrypted_api_key) as api_key:
            # Stricter validation: specific prefix, strict alphanumeric payload, minimum and maximum lengths
            if len(api_key) != 73 or not re.match(r"^sk-or-v1-[a-f0-9]{64}$", api_key):
                msg = "Decrypted API key does not match expected OpenRouter format."
                raise ValueError(msg)

            headers = {
                "Authorization": f"Bearer {api_key}",
            }

            payload = {
                "model": self._config.text_reasoning_model,
                "messages": [{"role": "user", "content": sanitized_prompt}],
            }

        try:
            response = await self._client.post(
                str(self._config.openrouter_api_url),
                json=payload,
                headers=headers,
                timeout=self._config.llm_timeout,
            )
            response.raise_for_status()

            try:
                data = response.json()
                return str(data["choices"][0]["message"]["content"])
            except ValueError as e:
                msg = "Failed to parse JSON response from LLM API."
                logger.exception(msg)
                raise LLMError(msg) from e

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code in (401, 403):
                msg = "Authentication failed (401/403)."
                logger.exception(
                    "HTTP status error during LLM generation. Check quota or endpoint."
                )
                raise LLMError(msg) from e
            if status_code == 429:
                msg = "Rate limit exceeded (429)."
                logger.warning(msg)
                raise LLMError(msg) from e
            logger.exception(f"HTTP error {status_code} during LLM generation.")
            msg = f"LLM API request failed due to an HTTP error: {status_code}."
            raise LLMError(msg) from e
        except httpx.RequestError as e:
            logger.exception("Network request error during LLM generation.")
            msg = "LLM API request failed due to a network error after retries."
            raise LLMError(msg) from e

    async def close(self) -> None:
        """Close the async client."""
        if self._client:
            await self._client.aclose()
            self._client = None
