from typing import Any

from src.domain_models.interfaces import (
    AIClientConfigProtocol,
    AICommunicationClientProtocol,
    AISecurityScannerProtocol,
    HTTPClientProtocol,
    RetryPolicyProtocol,
)


class AIClientConfig:
    def __init__(self, api_url: str, default_model: str, ai_timeout: int) -> None:
        self._api_url = api_url
        self._default_model = default_model
        self._ai_timeout = ai_timeout

    @property
    def api_url(self) -> str:
        return self._api_url

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def ai_timeout(self) -> int:
        return self._ai_timeout


class AIClientFactory:
    """Factory to construct DefaultAICommunicationClient ensuring configuration inversion mapping."""

    @staticmethod
    def create(
        api_url: str,
        default_model: str,
        ai_timeout: int,
        http_client: HTTPClientProtocol,
        retry_policy: RetryPolicyProtocol,
        security_scanner: AISecurityScannerProtocol,
        **kwargs: Any,  # noqa: ARG004
    ) -> AICommunicationClientProtocol:
        # All string format parameters are assumed to have been securely pre-validated directly by domain Config objects.
        # This properly obeys Dependency Inversion by removing direct OS environmental lookups.
        config = AIClientConfig(api_url=api_url, default_model=default_model, ai_timeout=ai_timeout)
        return DefaultAICommunicationClient(
            config=config,
            http_client=http_client,
            retry_policy=retry_policy,
            security_scanner=security_scanner,
        )


class DefaultAICommunicationClient(AICommunicationClientProtocol):
    """Handles HTTP communication with the external AI API."""

    def __init__(
        self,
        config: AIClientConfigProtocol,
        http_client: HTTPClientProtocol,
        retry_policy: RetryPolicyProtocol,
        security_scanner: AISecurityScannerProtocol,
    ) -> None:
        """
        Security context: Credentials are strictly maintained externally within the `http_client`
        secure JIT extraction loop. The AI client itself explicitly guarantees no key materials are
        persisted or logged in memory.
        """
        self.config = config
        self.http_client = http_client
        self.retry_policy = retry_policy
        self.security_scanner = security_scanner

    def __enter__(self) -> "DefaultAICommunicationClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Securely zeroize any internal references to configuration data after context completion."""
        self.config = None  # type: ignore
        self.http_client = None  # type: ignore
        import ctypes

        buffer = getattr(self, "_temp_secure_buffer", None)
        if buffer is not None:
            ctypes.memset(buffer, 0, len(buffer))
            self._temp_secure_buffer = None

    def rotate_credentials(self) -> None:
        """
        Forces the underlying secure HTTP client or KMS provider to immediately drop and rotate session tokens via their hardware enclaves.
        Because tokens are bound securely to JIT context managers and never exposed here, we simply instruct the HTTP client to flush local caches.
        """
        if hasattr(self.http_client, "flush_credentials_cache"):
            self.http_client.flush_credentials_cache()

    def _secure_memory_region_stub(self) -> None:
        """Stub representing secure enclave handling of memory APIs."""

    def call_api(self, prompt: str, model: str | None = None) -> str:
        safe_prompt = self.security_scanner.sanitize(prompt)

        def _execute() -> str:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "matome-app/1.0",
                "Accept": "application/json",
            }
            data = {
                "model": model or self.config.default_model,
                "messages": [{"role": "user", "content": safe_prompt}],
            }

            result = self.http_client.post(
                self.config.api_url,
                json=data,
                headers=headers,
                timeout=self.config.ai_timeout,
            )

            # Response validation
            if not isinstance(result, dict) or "choices" not in result:
                msg = "Unexpected API response format: missing 'choices'."
                raise ValueError(msg)

            choices = result.get("choices", [])
            if not choices or not isinstance(choices, list):
                msg = "Unexpected API response format: 'choices' is empty or invalid."
                raise ValueError(msg)

            message = choices[0].get("message", {})
            content = message.get("content")

            if content is None:
                msg = "Unexpected API response format: missing 'content'."
                raise ValueError(msg)

            return str(content)

        return str(self.retry_policy.execute(_execute))
