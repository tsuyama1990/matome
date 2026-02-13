"""
Verification Agent module.
This module implements the hallucination verification logic using an LLM.
"""

import json
import logging
import uuid

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from tenacity import Retrying, stop_after_attempt, wait_exponential

from domain_models.config import ProcessingConfig
from domain_models.verification import VerificationResult
from matome.config import get_openrouter_api_key, get_openrouter_base_url
from matome.exceptions import VerificationError
from matome.utils.prompts import VERIFICATION_TEMPLATE

logger = logging.getLogger(__name__)


class VerifierAgent:
    """
    Agent responsible for verifying summary content against source text.
    """

    def __init__(self, config: ProcessingConfig, llm: ChatOpenAI | None = None) -> None:
        """
        Initialize the VerifierAgent.

        Args:
            config: Processing configuration.
            llm: Optional pre-configured LLM instance.
        """
        self.config = config
        self.model_name = config.verification_model

        api_key = get_openrouter_api_key()
        base_url = get_openrouter_base_url()

        self.mock_mode = api_key == "mock"
        self.llm: ChatOpenAI | None = None

        if llm:
            self.llm = llm
        elif api_key and not self.mock_mode:
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0.0,  # Strict verification
                max_retries=config.max_retries,
                model_kwargs={"response_format": {"type": "json_object"}},  # Enforce JSON
            )
        else:
            self.llm = None

    def verify(self, summary: str, source_text: str) -> VerificationResult:
        """
        Verify the summary against the source text.

        Args:
            summary: The generated summary.
            source_text: The original source text (or combined chunks).

        Returns:
            VerificationResult containing score and details.
        """
        request_id = str(uuid.uuid4())

        if not summary or not source_text:
            logger.warning(f"[{request_id}] Empty summary or source text. Skipping verification.")
            return VerificationResult(
                score=0.0, model_name="Skipped", unsupported_claims=["Empty Input"]
            )

        if self.mock_mode:
            logger.info(f"[{request_id}] Mock mode enabled. Returning passed verification.")
            return VerificationResult(
                score=1.0, model_name="Mock", details=[], unsupported_claims=[]
            )

        if not self.llm:
            msg = f"[{request_id}] LLM not initialized. Cannot perform verification."
            logger.error(msg)
            raise VerificationError(msg)

        try:
            prompt = VERIFICATION_TEMPLATE.format(source_text=source_text, summary_text=summary)
            messages = [HumanMessage(content=prompt)]

            response = self._invoke_llm(messages, self.config, request_id)
            return self._process_response(response, request_id)

        except Exception as e:
            logger.exception(f"[{request_id}] Verification failed.")
            if isinstance(e, VerificationError):
                raise

            # Basic error categorization
            err_str = str(e).lower()
            if "context_length_exceeded" in err_str:
                msg = f"Verification failed: Context length exceeded. (Source length: {len(source_text)})"
            elif "rate_limit" in err_str:
                msg = "Verification failed: Rate limit exceeded."
            else:
                msg = f"Verification failed: {e}"

            raise VerificationError(msg) from e

    def _invoke_llm(
        self, messages: list[HumanMessage], config: ProcessingConfig, request_id: str
    ) -> BaseMessage:
        """Invoke LLM with retries."""
        if not self.llm:
            msg = "LLM not initialized"
            raise VerificationError(msg)

        response = None
        for attempt in Retrying(
            stop=stop_after_attempt(config.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        ):
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    logger.warning(
                        f"[{request_id}] Retrying Verification LLM call (Attempt {attempt.retry_state.attempt_number})"
                    )

                # Check invoke capability (standard ChatOpenAI has it)
                if hasattr(self.llm, "invoke"):
                    response = self.llm.invoke(messages)
                else:
                    response = self.llm(messages)  # type: ignore[operator]

        if not response:
            msg = f"[{request_id}] No response received from LLM."
            raise VerificationError(msg)

        return response

    def _process_response(self, response: BaseMessage, request_id: str) -> VerificationResult:
        """Parse JSON response from LLM."""
        content = response.content
        if not isinstance(content, str):
            content = str(content)

        # Basic cleanup for JSON
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]

        try:
            data = json.loads(content)
            # Ensure model name is set
            if "model_name" not in data:
                data["model_name"] = self.model_name

            return VerificationResult(**data)
        except json.JSONDecodeError as e:
            logger.exception(f"[{request_id}] Failed to parse JSON response: {content}")
            msg = f"Verification failed: Model returned invalid JSON. Response was: {content[:100]}..."
            raise VerificationError(msg) from e
        except Exception as e:
            logger.exception(f"[{request_id}] Validation failed for response data.")
            msg = f"Invalid verification result structure: {e}"
            raise VerificationError(msg) from e
