import logging
from typing import Any

import httpx
from pydantic import BaseModel, SecretStr

from src.domain_models import PipelineConfig
from src.domain_models.config import ApiCredentials
from src.interfaces import LLMError, LLMProtocol

logger = logging.getLogger(__name__)


class OpenRouterMessage(BaseModel):
    content: str | None = None


class OpenRouterChoice(BaseModel):
    message: OpenRouterMessage


class OpenRouterResponseSchema(BaseModel):
    choices: list[OpenRouterChoice]


class OpenRouterGateway(LLMProtocol):
    """An implementation of LLMProtocol that interfaces with the OpenRouter API."""

    def __init__(self, credentials: ApiCredentials, config: PipelineConfig, crypto_service: Any) -> None:
        self.credentials = credentials
        self.config = config
        self.crypto_service = crypto_service

    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        """Invokes the OpenRouter LLM with a prompt, timeout, and retry logic."""
        payload = self._prepare_payload(prompt, **kwargs)

        decrypted_key: SecretStr | None = self.credentials.get_decrypted_api_key(self.crypto_service)
        if not decrypted_key:
            msg = "Missing or invalid OpenRouter API key"
            raise LLMError(msg)

        # For secure memory wiping, we maintain the key in a mutable memoryview/bytearray
        # to ensure it can be natively overwritten without segfaulting the python GC
        # which expects strings to remain immutable at the C-level object header.
        secret_bytes = bytearray(f"Bearer {decrypted_key.get_secret_value()}", "utf-8")

        try:
            # We strictly yield a custom Auth object that utilizes memoryview to read the bytes directly.
            # However, since httpx strictly requires standard strings for headers, we decode it
            # specifically for the transmission window to minimize footprint.
            class EphemeralAuth(httpx.Auth):
                def __init__(self, secret_bytes: bytearray) -> None:
                    self.secret_bytes = secret_bytes

                def auth_flow(self, request: httpx.Request) -> Any:
                    # Decoding creates a transient string strictly bounded to the request dispatch
                    request.headers["Authorization"] = self.secret_bytes.decode(
                        "utf-8", errors="strict"
                    )
                    yield request

            headers = {
                "HTTP-Referer": self.config.app_domain,
                "X-Title": self.config.app_title,
                "Content-Type": "application/json",
            }

            with httpx.Client(timeout=timeout, auth=EphemeralAuth(secret_bytes), verify=True) as client:
                return self._execute_request(client, payload, headers, retries)
        finally:
            # Explicitly memory wipe the bytearray before GC
            for i in range(len(secret_bytes)):
                secret_bytes[i] = 0
            del secret_bytes
            del decrypted_key
            self.credentials.clear_cache()

    def _prepare_payload(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        model = kwargs.get("model", self.config.reasoning_model)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]

        return payload

    def _validate_dns_rebinding(self) -> None:
        import ipaddress
        import socket
        import urllib.parse
        parsed = urllib.parse.urlparse(self.config.openrouter_endpoint)
        hostname = parsed.hostname
        if not hostname:
            return
        try:
            current_ip = socket.gethostbyname(hostname)
            if self.config.openrouter_ip and current_ip != self.config.openrouter_ip:
                msg = "DNS Rebinding detected: IP does not match pinned IP."
                raise LLMError(msg)
            ip_obj = ipaddress.ip_address(current_ip)
            if ip_obj.is_private or ip_obj.is_loopback:
                msg = "DNS Rebinding detected: IP resolved to private/loopback."
                raise LLMError(msg)
        except socket.gaierror as e:
            msg = "Failed to resolve hostname for endpoint."
            raise LLMError(msg) from e

    def _execute_request(
        self, client: httpx.Client, payload: dict[str, Any], headers: dict[str, str], retries: int
    ) -> str:
        self._validate_dns_rebinding()
        for attempt in range(retries):
            try:
                return self._attempt_request(client, payload, headers)
            except Exception as e:
                self._handle_request_exception(e, attempt, retries)
        msg = "Failed to invoke OpenRouter after retries"
        raise LLMError(msg)

    def _attempt_request(self, client: httpx.Client, payload: dict[str, Any], headers: dict[str, str]) -> str:
        logger.debug("Sending request to OpenRouter")
        response = client.post(self.config.openrouter_endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return self._parse_response(response.json())

    def _handle_request_exception(self, e: Exception, attempt: int, retries: int) -> None:
        logger.warning(f"Error on attempt {attempt + 1}: {e}")
        if attempt == retries - 1:
            if isinstance(e, httpx.TimeoutException):
                msg = f"Timeout connecting to OpenRouter after {retries} attempts."
                raise LLMError(msg) from e
            if isinstance(e, httpx.HTTPStatusError):
                msg = f"OpenRouter API failed with status {e.response.status_code}: {e.response.text}"
                raise LLMError(msg) from e
            if isinstance(e, httpx.RequestError):
                msg = f"Network error connecting to OpenRouter: {e}"
                raise LLMError(msg) from e
            raise e

    def _parse_response(self, response_json: dict[str, Any]) -> str:
        try:
            # Validate against Pydantic schema
            validated_response = OpenRouterResponseSchema(**response_json)
        except Exception as e:
            logger.exception("Failed to validate OpenRouter response schema")
            msg = f"Invalid response format from OpenRouter: {response_json}"
            raise LLMError(msg) from e

        if not validated_response.choices:
            msg = f"Invalid response format from OpenRouter: {response_json}"
            raise LLMError(msg)

        content = validated_response.choices[0].message.content
        if content is None:
            msg = "Missing content in OpenRouter response"
            raise LLMError(msg)

        return str(content)
