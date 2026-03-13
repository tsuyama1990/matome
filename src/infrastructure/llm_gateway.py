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

    def __init__(self, original_backend: httpcore.AsyncNetworkBackend, allowed_hosts: list[str]) -> None:
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
        if host not in self._allowed_hosts:
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


class SecureAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """HTTP transport with secure network backend injection."""

    def __init__(self, allowed_hosts: list[str], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        original_backend = self._pool._network_backend
        protected_backend = SSRFProtectedBackend(
            original_backend=original_backend,
            allowed_hosts=allowed_hosts
        )
        self._pool._network_backend = protected_backend


class OpenRouterGateway:
    """Gateway for OpenRouter API."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config

        transport = SecureAsyncHTTPTransport(allowed_hosts=self._config.allowed_hosts)

        self._client = httpx.AsyncClient(
            timeout=self._config.llm_timeout,
            transport=transport
        )

    async def generate(self, prompt: str) -> str:
        """Generates text from a prompt."""
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key or len(api_key.strip()) < 10:
            msg = "OPENROUTER_API_KEY environment variable is missing or invalid."
            raise ValueError(msg)

        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
        }

        payload = {
            "model": self._config.text_reasoning_model,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            response = await self._client.post(
                str(self._config.openrouter_api_url),
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            return str(data["choices"][0]["message"]["content"])

        except httpx.HTTPStatusError as e:
            # Sanitize error
            logger.exception("HTTP status error during LLM generation. Check API key and quota.")
            msg = "LLM API request failed due to an HTTP error."
            raise LLMError(msg) from e
        except httpx.RequestError as e:
            logger.exception("Network request error during LLM generation.")
            msg = "LLM API request failed due to a network error."
            raise LLMError(msg) from e

    async def close(self) -> None:
        """Close the async client."""
        await self._client.aclose()
