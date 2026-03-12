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

        # Ensure the provided hostname itself is not directly a private IP before DNS resolution
        try:
            ip_obj = ipaddress.ip_address(hostname)
            if ip_obj.is_private or ip_obj.is_loopback:
                msg = "SSRF Attempt Blocked: Hostname is a private IP"
                raise LLMError(msg)
        except ValueError:
            pass  # It's a valid hostname, not an IP, proceed to resolution

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
                # Reject connections that don't match the pinned host
                if host != self.pinned_host:
                    msg = f"Connection to {host} rejected. Only connections to {self.pinned_host} are allowed."
                    raise RuntimeError(msg)

                # Replace with pinned IP
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

        # Delay httpx client creation until the first invoke to dynamically construct the pinned transport.
        import threading

        self._client: httpx.Client | None = None
        self._circuit_breaker_fails: int = 0
        self._circuit_breaker_open_until: float = 0.0
        self._lock = threading.Lock()

    def _validate_referer(self, value: str) -> None:
        import re
        import urllib.parse

        try:
            parsed = urllib.parse.urlparse(value)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                msg = "HTTP-Referer is not a valid URL."
                raise ValueError(msg)  # noqa: TRY301
            # Also enforce safe characters in the serialized string
            if not re.match(r"^https?://[a-zA-Z0-9\-\._~:/?#\[\]@!$&'()*+,;=]+$", value):
                msg = "HTTP-Referer contains invalid characters."
                raise ValueError(msg)  # noqa: TRY301
        except ValueError as e:
            raise LLMError(str(e)) from e

    def _sanitize_header(self, value: str, field: str) -> str:
        """Strictly sanitizes headers against injection attacks using field-specific whitelists."""
        import re

        if field == "HTTP-Referer":
            self._validate_referer(value)
        elif field == "X-Title":
            if not re.match(r"^[a-zA-Z0-9 \-\._]+$", value):
                msg = "X-Title contains invalid characters."
                raise LLMError(msg)
        elif field == "Content-Type":
            if not re.match(r"^[a-zA-Z0-9/\-\._]+(; *[a-zA-Z0-9\-\._]+=[a-zA-Z0-9\-\._]+)?$", value):
                msg = "Content-Type contains invalid characters."
                raise LLMError(msg)
        elif field == "Authorization":
            if not re.match(r"^Bearer sk-or-v1-[a-zA-Z0-9]{64}$", value):
                msg = "Authorization contains invalid characters."
                raise LLMError(msg)
        elif not re.match(r"^[a-zA-Z0-9\-\._]+$", value):
            msg = "Header value contains invalid characters."
            raise LLMError(msg)
        return value

    def invoke(self, prompt: str, timeout: int = 30, retries: int = 3, **kwargs: Any) -> str:
        """Invokes the OpenRouter LLM with a prompt, timeout, and retry logic."""
        import time

        with self._lock:
            # Ensure key is encrypted in memory inside the lock before using it
            if self.credentials.openrouter_api_key is not None:
                self.credentials.encrypt_key(self.crypto_service)

            if time.time() < self._circuit_breaker_open_until:
                msg = "Circuit breaker is open. Request rejected."
                raise LLMError(msg)

            payload = self._prepare_payload(prompt, **kwargs)

            safe_domain = self._sanitize_header(self.config.app_domain, "HTTP-Referer")
            safe_title = self._sanitize_header(self.config.app_title, "X-Title")

            # We use a context manager to retrieve and clear the decrypted key from cache securely
            with self.credentials.decrypted_key_context(self.crypto_service) as decrypted_key:
                if not decrypted_key:
                    msg = "Missing or invalid OpenRouter API key"
                    raise LLMError(msg)

                api_key_str = decrypted_key.get_secret_value()

                # Construct headers strictly inside the context block so we do not pass the raw decrypted key out of context unnecessarily.
                # The Authorization header is sanitized before assignment.
                headers = {
                    "HTTP-Referer": safe_domain,
                    "X-Title": safe_title,
                    "Content-Type": self._sanitize_header("application/json", "Content-Type"),
                    "Authorization": self._sanitize_header(
                        f"Bearer {api_key_str}", "Authorization"
                    ),
                }

        parsed_url = urllib.parse.urlparse(self.config.openrouter_endpoint)
        hostname = parsed_url.hostname
        if not hostname:
            msg = "Invalid endpoint URL"
            raise LLMError(msg)

        # Resolve once to prevent TOCTOU SSRF vulnerabilities
        ip = self.dns_resolver.resolve_and_validate_ip(hostname, self.config.allowed_api_domains)

        with self._lock:
            if self._client is None:
                transport = self.dns_resolver.create_pinned_transport(hostname, ip)
                self._client = httpx.Client(
                    transport=transport,
                    verify=True,
                    limits=httpx.Limits(
                        max_keepalive_connections=100, max_connections=100, keepalive_expiry=300
                    ),
                )
            client = self._client

        try:
            result = self._execute_request(client, payload, headers, retries, timeout=timeout)
            with self._lock:
                self._circuit_breaker_fails = 0
        except LLMError:
            with self._lock:
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
        """Safely streams and parses the JSON response incrementally using true streaming to avoid memory exhaustion."""
        import io

        import ijson

        response.raise_for_status()

        class StreamIOWrapper(io.RawIOBase):
            def __init__(self, stream: httpx.Response, check_limit: Any, max_size: int) -> None:
                self.iterator = stream.iter_bytes(chunk_size=4096)
                self.current_bytes = 0
                self.check_limit = check_limit
                self.max_size = max_size
                self.buffer = b""

            def readinto(self, b: bytearray) -> int:
                # ijson relies on readinto for RawIOBase
                size = len(b)
                while len(self.buffer) < size:
                    try:
                        chunk = next(self.iterator)
                        self.current_bytes += len(chunk)
                        self.check_limit(self.current_bytes, self.max_size)
                        self.buffer += chunk
                    except StopIteration:
                        break

                if not self.buffer:
                    return 0

                chunk_size = min(size, len(self.buffer))
                b[:chunk_size] = self.buffer[:chunk_size]
                self.buffer = self.buffer[chunk_size:]
                return chunk_size

            def readable(self) -> bool:
                return True

        stream_io = StreamIOWrapper(
            response, self._check_stream_limit, self.config.max_response_bytes
        )

        try:
            # We use ijson for truly incremental memory-safe parsing of JSON streams
            # It will parse objects sequentially without holding the full string in memory.
            # ijson expects byte streams.
            parser = ijson.items(stream_io, "", use_float=True)
            result = next(parser)

            # Read out the rest to ensure HTTP response gets properly exhausted if there's any trailing bytes
            for _ in parser:
                pass
        except (ijson.JSONError, StopIteration, ValueError) as e:
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
                    timeout=httpx.Timeout(timeout),
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
        # Pre-validate structure manually before Pydantic to ensure safe property access
        if not isinstance(response_json, dict):
            msg = "Invalid response format from OpenRouter: Expected dictionary"
            raise LLMError(msg)

        if "choices" not in response_json or not isinstance(response_json["choices"], list):
            msg = "Invalid response format from OpenRouter: Missing or invalid 'choices'"
            raise LLMError(msg)

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

        first_choice = validated_response.choices[0]
        if not hasattr(first_choice, "message") or first_choice.message is None:
            msg = "Missing message in OpenRouter response"
            raise LLMError(msg)

        content = first_choice.message.content
        if content is None:
            msg = "Missing content in OpenRouter response"
            raise LLMError(msg)

        return str(content)
