import ipaddress
import logging
import os
import socket
from typing import Any

import httpcore
import httpx

from src.config.settings import ModelConfig

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM operations."""


class SSRFProtectedBackend(httpcore.AsyncNetworkBackend):
    """Custom network backend to prevent SSRF and DNS Rebinding."""

    def __init__(
        self, original_backend: httpcore.AsyncNetworkBackend, allowed_hosts: list[str]
    ) -> None:
        self._original_backend = original_backend
        self._allowed_hosts = allowed_hosts

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any | None = None,
    ) -> httpcore.AsyncNetworkStream:
        """Connects via TCP with strict IP validation."""
        host_lower = host.lower()
        is_allowed = any(
            host_lower == allowed_host.lower() or host_lower.endswith(f".{allowed_host.lower()}")
            for allowed_host in self._allowed_hosts
        )
        if not is_allowed:
            msg = f"Host {host} is not in the allowed list."
            raise ValueError(msg)

        try:
            addr_info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
            ip: str = str(addr_info[0][4][0])
        except socket.gaierror as e:
            msg = f"DNS resolution failed for {host}"
            raise ValueError(msg) from e

        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback:
            msg = "SSRF Attempt: Disallowed private or loopback IP."
            raise ValueError(msg)

        return await self._original_backend.connect_tcp(
            ip, port, timeout=timeout, local_address=local_address, socket_options=socket_options
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Any | None = None,
    ) -> httpcore.AsyncNetworkStream:
        """Connects via UNIX socket."""
        return await self._original_backend.connect_unix_socket(
            path, timeout=timeout, socket_options=socket_options
        )


class SecureAsyncHTTPTransport(httpx.AsyncBaseTransport):
    """
    HTTP transport with secure network backend injection and retry logic.

    It mitigates Server-Side Request Forgery (SSRF) and DNS Rebinding attacks by independently
    resolving the DNS, strictly matching the target against an allowed hosts list,
    and blocking any resolutions to private or loopback IP addresses before the
    TCP connection is established. It preserves TLS SNI functionality.
    It also implements resilient retry logic for network errors at the transport layer.
    """

    def __init__(self, allowed_hosts: list[str], **kwargs: Any) -> None:
        super().__init__()
        import re

        # Validate structurally valid domains
        domain_regex = re.compile(
            r"^(?:[a-zA-Z0-9]"
            r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
            r"[a-zA-Z]{2,6}\.?$"
        )
        for host in allowed_hosts:
            if not domain_regex.match(host) and host != "localhost":
                msg = f"Invalid domain name in allowed_hosts: {host}"
                raise ValueError(msg)

        from httpcore._backends.anyio import AnyIOBackend
        original_backend = AnyIOBackend()
        protected_backend = SSRFProtectedBackend(
            original_backend=original_backend, allowed_hosts=allowed_hosts
        )

        # Instantiate pool explicitly with kwargs (like limits, verify) safely mapped
        # to what httpcore expects, or simply use defaults and pass network_backend
        self._pool = httpcore.AsyncConnectionPool(network_backend=protected_backend)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(httpx.RequestError),
            reraise=True,
        )
        async def _execute() -> httpx.Response:
            # Map httpx.Request to httpcore.Request
            req = httpcore.Request(
                method=request.method,
                url=httpcore.URL(
                    scheme=request.url.scheme.encode("ascii"),
                    host=request.url.host.encode("ascii"),
                    port=request.url.port,
                    target=request.url.raw_path,
                ),
                headers=request.headers.raw,
                content=request.stream,
                extensions=request.extensions,
            )
            resp = await self._pool.handle_async_request(req)
            return httpx.Response(
                status_code=resp.status,
                headers=resp.headers,
                stream=resp.stream,  # type: ignore[arg-type]
                extensions=resp.extensions,
            )

        return await _execute()


class OpenRouterGateway:
    """Gateway for OpenRouter API."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None
        self._encrypted_api_key = os.environ.get("OPENROUTER_API_KEY_ENCRYPTED")

        # Verify ENCRYPTION_KEY exists
        enc_key = os.environ.get("ENCRYPTION_KEY")
        if not enc_key or len(enc_key.strip()) < 44:
            msg = "ENCRYPTION_KEY environment variable is missing or invalid format."
            raise ValueError(msg)

        if not self._config.openrouter_api_url or not self._config.text_reasoning_model:
            msg = "Invalid ModelConfig: URL or model name is missing."
            raise ValueError(msg)

        if not self._encrypted_api_key:
            msg = "OPENROUTER_API_KEY_ENCRYPTED environment variable is missing."
            raise ValueError(msg)

    async def __aenter__(self) -> "OpenRouterGateway":
        transport = SecureAsyncHTTPTransport(allowed_hosts=self._config.allowed_hosts)
        # Using verify=True explicitly to ensure strict SSL verification as requested
        self._client = httpx.AsyncClient(
            timeout=self._config.llm_timeout, transport=transport, verify=True
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def generate(self, prompt: str) -> str:
        """Generates text from a prompt."""
        import re

        from src.config.security import SecurityService

        if not self._client:
            msg = "Client not initialized. Use async context manager."
            raise RuntimeError(msg)

        # Sanitize prompt
        sanitized_prompt = "".join(char for char in prompt if char.isprintable() or char in "\n\r\t")
        if len(sanitized_prompt) > 100000:
            msg = "Prompt exceeds maximum allowed length."
            raise ValueError(msg)

        security_service = SecurityService()
        with security_service.get_decrypted_key(self._encrypted_api_key) as api_key:  # type: ignore[arg-type]
            if len(api_key) < 20 or not re.match(r"^sk-[A-Za-z0-9\-_]+$", api_key):
                msg = "Decrypted API key does not match expected format."
                raise ValueError(msg)

            headers = {
                "Authorization": f"Bearer {api_key}",
            }

            payload = {
                "model": self._config.text_reasoning_model,
                "messages": [{"role": "user", "content": sanitized_prompt}],
            }

        if not self._client:
            msg = "Client not initialized."
            raise RuntimeError(msg)

        try:
            response = await self._client.post(
                str(self._config.openrouter_api_url),
                json=payload,
                headers=headers,
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
