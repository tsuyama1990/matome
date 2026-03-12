import ipaddress
import logging
import socket
import urllib.parse
from typing import Any

import httpcore
import httpx
from pydantic import BaseModel

from src.domain_models import PipelineConfig
from src.domain_models.config import ApiCredentials
from src.infrastructure.crypto import CryptoService
from src.interfaces import LLMError, LLMProtocol

logger = logging.getLogger(__name__)


class DNSResolver:
    """Service dedicated to securely resolving and validating DNS, protecting against SSRF."""

    def resolve_and_validate_ip(self, hostname: str, allowed_domains: list[str]) -> str:
        """Resolves the hostname and validates it against allowed domains and private/loopback IPs."""
        # First, extract just the hostname from the allowed domains for matching
        allowed_hostnames = []
        for domain in allowed_domains:
            parsed = urllib.parse.urlparse(domain)
            if parsed.hostname:
                allowed_hostnames.append(parsed.hostname)

        # STRICT RULE: Hostname validation MUST occur BEFORE DNS resolution to prevent DNS rebinding attacks.
        # Check if hostname ends with any allowed domain (for subdomain support), or exact match
        is_allowed = any(hostname == h or hostname.endswith("." + h) for h in allowed_hostnames)
        if not is_allowed:
            msg = f"Hostname {hostname} is not in the allowed API domains whitelist."
            raise LLMError(msg)

        # Only resolve after strict validation
        try:
            ip = socket.gethostbyname(hostname)
        except socket.gaierror as e:
            msg = "Failed to resolve hostname"
            raise LLMError(msg) from e

        # Ensure the resolved IP itself does not hit private internal networks
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback:
            msg = "SSRF Attempt Blocked"
            raise LLMError(msg)

        return ip

    def create_pinned_transport(self, hostname: str, ip: str) -> httpx.HTTPTransport:
        """Creates an httpx HTTPTransport that natively pins the DNS resolution, completely avoiding monkeypatching."""

        class PinnedNetworkBackend(httpcore.NetworkBackend):
            def __init__(self, pinned_host: str, pinned_ip: str) -> None:
                self.pinned_host = pinned_host
                self.pinned_ip = pinned_ip
                self.backend = httpcore.SyncBackend()

            def connect_tcp(
                self,
                host: str,
                port: int,
                timeout: float | None = None,
                local_address: str | None = None,
                socket_options: Any = None,
            ) -> httpcore.NetworkStream:
                # Intercept the connection host if it matches our pinned target
                if host == self.pinned_host:
                    host = self.pinned_ip
                return self.backend.connect_tcp(host, port, timeout, local_address, socket_options)

            def connect_unix_socket(self, *args: Any, **kwargs: Any) -> httpcore.NetworkStream:
                return self.backend.connect_unix_socket(*args, **kwargs)

            def sleep(self, *args: Any, **kwargs: Any) -> None:
                return self.backend.sleep(*args, **kwargs)

        ssl_context = httpx.create_ssl_context()
        pool = httpcore.ConnectionPool(
            ssl_context=ssl_context,
            network_backend=PinnedNetworkBackend(hostname, ip),
            max_connections=100,
            max_keepalive_connections=100,
            keepalive_expiry=300.0,
        )
        transport = httpx.HTTPTransport(verify=True)
        # Inject the custom pool directly into the transport
        transport._pool = pool
        return transport


class OpenRouterMessage(BaseModel):
    content: str | None = None


class OpenRouterChoice(BaseModel):
    message: OpenRouterMessage


class OpenRouterResponseSchema(BaseModel):
    choices: list[OpenRouterChoice]


class OpenRouterGateway(LLMProtocol):
    """An implementation of LLMProtocol that interfaces with the OpenRouter API."""

    def __init__(
        self,
        credentials: ApiCredentials,
        config: PipelineConfig,
        dns_resolver: DNSResolver,
        crypto_service: CryptoService,
    ) -> None:
        self.credentials = credentials
        self.config = config
        self.dns_resolver = dns_resolver
        self.crypto_service = crypto_service

        # Ensure key is encrypted in memory
        if self.credentials.openrouter_api_key is not None:
            self.credentials.encrypt_key(self.crypto_service)

        # Delay httpx client creation until the first invoke to dynamically construct the pinned transport.
        self._client: httpx.Client | None = None
        self._circuit_breaker_fails: int = 0
        self._circuit_breaker_open_until: float = 0.0

    def _sanitize_header(self, value: str) -> str:
        """Strictly sanitizes headers against injection attacks using a whitelist approach."""
        import re

        # Validate against known safe header values (whitelist approach)
        if not re.match(r"^[a-zA-Z0-9_ \-.:/]+$", value):
            msg = "Header value contains invalid characters."
            raise LLMError(msg)
        return value

    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        """Invokes the OpenRouter LLM with a prompt, timeout, and retry logic."""
        import time

        if time.time() < self._circuit_breaker_open_until:
            msg = "Circuit breaker is open. Request rejected."
            raise LLMError(msg)

        payload = self._prepare_payload(prompt, **kwargs)

        # We use a context manager to retrieve and clear the decrypted key from cache securely
        with self.credentials.decrypted_key_context(self.crypto_service) as decrypted_key:
            if not decrypted_key:
                msg = "Missing or invalid OpenRouter API key"
                raise LLMError(msg)

            safe_domain = self._sanitize_header(self.config.app_domain)
            safe_title = self._sanitize_header(self.config.app_title)

            headers = {
                "HTTP-Referer": safe_domain,
                "X-Title": safe_title,
                "Content-Type": "application/json",
                "Authorization": f"Bearer {decrypted_key.get_secret_value()}",
            }

            parsed_url = urllib.parse.urlparse(self.config.openrouter_endpoint)
            hostname = parsed_url.hostname
            if not hostname:
                msg = "Invalid endpoint URL"
                raise LLMError(msg)

            # Resolve once to prevent TOCTOU SSRF vulnerabilities
            ip = self.dns_resolver.resolve_and_validate_ip(
                hostname, self.config.allowed_api_domains
            )

            if self._client is None:
                transport = self.dns_resolver.create_pinned_transport(hostname, ip)
                self._client = httpx.Client(
                    transport=transport,
                    verify=True,
                    timeout=httpx.Timeout(timeout),
                    limits=httpx.Limits(
                        max_keepalive_connections=100, max_connections=100, keepalive_expiry=300
                    ),
                )

            try:
                result = self._execute_request(
                    self._client, payload, headers, retries, timeout=timeout
                )
                self._circuit_breaker_fails = 0
            except LLMError:
                self._circuit_breaker_fails += 1
                if self._circuit_breaker_fails >= 5:
                    # Open circuit for 60 seconds
                    self._circuit_breaker_open_until = time.time() + 60
                raise
            else:
                return result

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

    def _check_stream_limit(self, current_bytes: int, max_size: int) -> None:
        if current_bytes > max_size:
            msg = "Response size exceeded maximum allowed limit"
            raise LLMError(msg)

    def _process_stream_response(self, response: httpx.Response) -> dict[str, Any]:
        """Safely streams and parses the JSON response to avoid memory exhaustion."""
        import json

        response.raise_for_status()

        # To resolve complexity issues and preserve memory validation,
        # we iterate the raw stream, aggressively checking length before accumulating.
        raw_bytes = bytearray()
        for chunk in response.iter_bytes():
            self._check_stream_limit(len(raw_bytes) + len(chunk), self.config.max_response_bytes)
            raw_bytes.extend(chunk)

        try:
            result = json.loads(raw_bytes.decode("utf-8"))
        except json.JSONDecodeError as e:
            msg = "Failed to parse JSON response"
            raise LLMError(msg) from e
        else:
            if not isinstance(result, dict):
                msg = "JSON response is not a dictionary"
                raise LLMError(msg)
            return result

    def _execute_request(
        self,
        client: httpx.Client,
        payload: dict[str, Any],
        headers: dict[str, str],
        retries: int,
        timeout: int = 30,
    ) -> str:
        import time

        for attempt in range(retries):
            try:
                logger.debug(f"Sending request to OpenRouter (Attempt {attempt + 1}/{retries})")
                with client.stream(
                    "POST",
                    self.config.openrouter_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                ) as response:
                    response_json = self._process_stream_response(response)
                    return self._parse_response(response_json)

            except httpx.TimeoutException as e:
                logger.warning("OpenRouter API request timed out on attempt")
                if attempt == retries - 1:
                    msg = "OpenRouter API request failed due to timeout."
                    raise LLMError(msg) from e
            except httpx.HTTPStatusError as e:
                logger.warning("OpenRouter API request failed due to HTTP error")
                if attempt == retries - 1:
                    msg = "OpenRouter API request failed"
                    raise LLMError(msg) from e
            except httpx.RequestError as e:
                logger.warning("OpenRouter API request encountered a network error")
                if attempt == retries - 1:
                    msg = "OpenRouter API request failed due to network error"
                    raise LLMError(msg) from e

            # Exponential backoff with jitter
            import secrets

            sleep_time = (2**attempt) + (secrets.randbelow(100) / 100.0)
            time.sleep(sleep_time)

        msg = "Failed to invoke OpenRouter API after retries"
        raise LLMError(msg)

    def _parse_response(self, response_json: dict[str, Any]) -> str:
        try:
            # Validate against Pydantic schema
            validated_response = OpenRouterResponseSchema(**response_json)
        except (TypeError, ValueError) as e:
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
