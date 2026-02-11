"""
Module for verifying the accuracy of generated summaries using an LLM.
"""

import json
import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr, ValidationError
from tenacity import Retrying, stop_after_attempt, wait_exponential

from domain_models.config import ProcessingConfig
from domain_models.verification import VerificationResult
from matome.config import get_openrouter_api_key, get_openrouter_base_url
from matome.exceptions import VerificationError
from matome.utils.prompts import VERIFICATION_TEMPLATE

logger = logging.getLogger(__name__)


class VerifierAgent:
    """
    Agent responsible for verifying summaries against source text.
    """

    def __init__(self, config: ProcessingConfig, llm: ChatOpenAI | None = None) -> None:
        """
        Initialize the VerifierAgent.

        Args:
            config: Processing configuration.
            llm: Optional LLM instance for testing.
        """
        self.config = config
        self.model_name = config.verification_model

        # Determine API key and Base URL
        api_key = get_openrouter_api_key()
        base_url = get_openrouter_base_url()

        self.mock_mode = api_key == "mock"

        if llm:
            self.llm: ChatOpenAI | None = llm
        elif api_key and not self.mock_mode:
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=SecretStr(api_key),
                base_url=base_url,
                temperature=0.0,  # Deterministic for verification
                max_retries=config.max_retries,
            )
        else:
            self.llm = None

    def verify(self, summary: str, source_text: str) -> VerificationResult:
        """
        Verify the summary against the source text.

        Args:
            summary: The generated summary to verify.
            source_text: The original text chunks used to generate the summary.

        Returns:
            VerificationResult object containing score and details.

        Raises:
            VerificationError: If verification fails.
        """
        request_id = str(uuid.uuid4())

        if self.mock_mode:
            logger.info(f"[{request_id}] Mock mode enabled. Returning perfect verification.")
            return VerificationResult(score=1.0, details=[], unsupported_claims=[], model_name="mock")

        if not self.llm:
            msg = "LLM not initialized (missing API Key?). Cannot perform verification."
            logger.error(msg)
            raise VerificationError(msg)

        # Truncate source text if too long (naive approach, but better than crashing)
        # Using 100k chars as reasonable limit for typical LLM context windows
        MAX_VERIFICATION_CHARS = 100_000
        if len(source_text) > MAX_VERIFICATION_CHARS:
            logger.warning(
                f"Source text too long for verification ({len(source_text)} chars). "
                f"Truncating to {MAX_VERIFICATION_CHARS}."
            )
            source_text = source_text[:MAX_VERIFICATION_CHARS]

        prompt = VERIFICATION_TEMPLATE.format(source_text=source_text, summary_text=summary)
        messages = [HumanMessage(content=prompt)]

        try:
            response_content = self._invoke_llm(messages, request_id)
            return self._parse_response(response_content, request_id)
        except Exception as e:
            logger.exception(f"[{request_id}] Verification failed.")
            error_str = str(e).lower()
            if "context_length_exceeded" in error_str:
                msg = "Context length exceeded during verification."
                raise VerificationError(msg) from e
            if "rate_limit" in error_str:
                msg = "Rate limit exceeded during verification."
                raise VerificationError(msg) from e
            msg = f"Verification failed: {e}"
            raise VerificationError(msg) from e

    def _invoke_llm(self, messages: list[HumanMessage], request_id: str) -> str:
        """Invoke LLM with retries."""
        if not self.llm:
            msg = "LLM not initialized"
            raise VerificationError(msg)

        response = None
        for attempt in Retrying(
            stop=stop_after_attempt(self.config.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        ):
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    logger.warning(
                        f"[{request_id}] Retrying Verification LLM call (Attempt {attempt.retry_state.attempt_number})"
                    )
                response = self.llm.invoke(messages)

        if not response:
            msg = "No response from LLM"
            raise VerificationError(msg)

        content = response.content
        if isinstance(content, str):
            return content
        return str(content)

    def _parse_response(self, content: str, request_id: str) -> VerificationResult:
        """Parse JSON response from LLM."""
        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        if clean_content.startswith("```"):
            clean_content = clean_content[3:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]

        try:
            # Parse into dict first to inject model_name
            data: dict[str, Any] = json.loads(clean_content.strip())
            data["model_name"] = self.model_name
            return VerificationResult(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.exception(f"[{request_id}] Failed to parse verification result: {content}")
            msg = f"Invalid JSON response from verification model: {e}"
            raise VerificationError(msg) from e
