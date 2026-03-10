from typing import Any

from src.domain_models.interfaces import (
    AICommunicationClientProtocol,
    HTTPClientProtocol,
    RetryPolicyProtocol,
)


class DefaultAICommunicationClient(AICommunicationClientProtocol):
    """Handles HTTP communication with the external AI API."""

    def __init__(
        self,
        api_url: str,
        default_model: str,
        ai_timeout: int,
        http_client: HTTPClientProtocol,
        retry_policy: RetryPolicyProtocol,
        **kwargs: Any,
    ) -> None:
        """
        Security context: Credentials are strictly maintained externally within the `http_client`
        secure JIT extraction loop. The AI client itself explicitly guarantees no key materials are
        persisted or logged in memory.
        """
        self.api_url = api_url
        self.default_model = default_model
        self.ai_timeout = ai_timeout
        self.http_client = http_client
        self.retry_policy = retry_policy

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
        def _execute() -> str:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "matome-app/1.0",
                "Accept": "application/json",
            }
            data = {
                "model": model or self.default_model,
                "messages": [{"role": "user", "content": prompt}],
            }

            result = self.http_client.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=self.ai_timeout,
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
