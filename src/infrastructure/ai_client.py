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
        self.credential_provider = credential_provider  # Still accept but ignore here (or wait, I can't edit container.py, so I must accept it)
        self.api_url = api_url
        self.default_model = default_model
        self.ai_timeout = ai_timeout
        self.http_client = http_client
        self.retry_policy = retry_policy

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
