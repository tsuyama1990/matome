import ipaddress
import logging
import socket
from typing import Any

import httpcore
import httpx

logger = logging.getLogger(__name__)


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
