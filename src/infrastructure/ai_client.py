from src.domain_models.interfaces import (
    AICommunicationClientProtocol,
    CredentialProviderProtocol,
    HTTPClientProtocol,
    RetryPolicyProtocol,
)


class DefaultAICommunicationClient(AICommunicationClientProtocol):
    """Handles HTTP communication with the external AI API."""

    def __init__(
        self,
        credential_provider: CredentialProviderProtocol,
        api_url: str,
        default_model: str,
        ai_timeout: int,
        http_client: HTTPClientProtocol,
        retry_policy: RetryPolicyProtocol,
    ) -> None:
        self.credential_provider = credential_provider
        self.api_url = api_url
        self.default_model = default_model
        self.ai_timeout = ai_timeout
        self.http_client = http_client
        self.retry_policy = retry_policy

    def call_api(self, prompt: str, model: str | None = None) -> str:
        def _execute() -> str:
            with self.credential_provider.get_api_key() as secure_key:
                headers = {
                    "Content-Type": "application/json",
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
                    verify=True,  # Explicitly force SSL/TLS certificate validation
                    auth_token=secure_key,
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
