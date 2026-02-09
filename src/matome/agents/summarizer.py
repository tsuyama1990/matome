"""
Summarization Agent module.
This module implements the summarization logic using OpenRouter and Chain of Density prompting.
"""
import logging
import os
import re
import uuid
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from tenacity import stop_after_attempt, wait_exponential

from domain_models.config import ProcessingConfig
from matome.config import get_openrouter_api_key, get_openrouter_base_url
from matome.exceptions import SummarizationError
from matome.utils.constants import DEFAULT_SUMMARIZATION_MODEL
from matome.utils.prompts import COD_TEMPLATE

logger = logging.getLogger(__name__)


class SummarizationAgent:
    """
    Agent responsible for summarizing text using an LLM.
    """

    def __init__(self, model_name: str | None = None) -> None:
        """
        Initialize the SummarizationAgent.

        Args:
            model_name: The name of the model to use. If None, uses SUMMARIZATION_MODEL env var
                        or defaults to DEFAULT_SUMMARIZATION_MODEL.
        """
        # Retrieve API key securely from environment via config utility
        api_key = get_openrouter_api_key()
        base_url = get_openrouter_base_url()

        # Determine model name
        self.model_name = model_name or os.getenv("SUMMARIZATION_MODEL", DEFAULT_SUMMARIZATION_MODEL)

        self.api_key = api_key
        self.llm: ChatOpenAI | None = None

        # Initialize LLM only if API key is present (or if we want to allow failure later)
        # Check for 'mock' value explicitly to enable testing mode without real calls
        if api_key and api_key != "mock":
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0,
                max_retries=1, # We handle retries via tenacity wrapper now
            )

    def summarize(self, text: str, config: ProcessingConfig) -> str:
        """
        Summarize the provided text using the Chain of Density strategy.

        Args:
            text: The text to summarize.
            config: Configuration parameters.

        Returns:
            The generated summary.

        Raises:
            SummarizationError: If summarization fails or API key is missing.
        """
        request_id = str(uuid.uuid4())

        if not text:
            logger.debug(f"[{request_id}] Skipping empty text summarization.")
            return ""

        # Validate input for security
        self._validate_input(text)

        # Mock Mode Check
        if self.api_key == "mock":
            logger.info(f"[{request_id}] Mock mode enabled. Returning static summary.")
            return f"Summary of {text[:20]}..."

        if not self.llm:
            msg = f"[{request_id}] OpenRouter API Key is missing. Cannot perform summarization."
            logger.error(msg)
            raise SummarizationError(msg)

        if config.summarization_model != self.model_name:
             logger.debug(f"[{request_id}] Config model {config.summarization_model} differs from agent model {self.model_name}. Using agent model.")

        try:
            prompt = COD_TEMPLATE.format(context=text)
            messages = [HumanMessage(content=prompt)]

            response = self._invoke_llm(messages, config, request_id)
            return self._process_response(response, request_id)

        except Exception as e:
            # Enhanced error logging with custom exception
            logger.exception(f"[{request_id}] Summarization failed for text length {len(text)}")
            msg = f"Summarization failed: {e}"
            raise SummarizationError(msg) from e

    def _validate_input(self, text: str) -> None:
        """
        Sanitize and validate input text to prevent injection attacks or excessive load.
        """
        # 1. Length Check
        # Assuming extremely large inputs might be a DoS vector.
        # But this is summarization, so large inputs are expected.
        # Let's set a reasonable upper bound if needed, e.g., 100k chars for now.
        MAX_INPUT_LENGTH = 500_000
        if len(text) > MAX_INPUT_LENGTH:
             msg = f"Input text exceeds maximum allowed length ({MAX_INPUT_LENGTH} characters)."
             raise ValueError(msg)

        # 2. Control Character Check
        # Remove null bytes and other dangerous control characters, preserving newlines/tabs
        # Use regex to find control characters (C0 and C1) excluding CR, LF, Tab
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
             msg = "Input text contains invalid control characters."
             raise ValueError(msg)

    def _invoke_llm(self, messages: list[HumanMessage], config: ProcessingConfig, request_id: str) -> BaseMessage:
        """Helper to invoke LLM with retry logic."""
        if not self.llm:
             msg = "LLM not initialized"
             raise SummarizationError(msg)

        from tenacity import Retrying

        response = None
        for attempt in Retrying(
            stop=stop_after_attempt(config.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        ):
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    logger.warning(f"[{request_id}] Retrying LLM call (Attempt {attempt.retry_state.attempt_number}/{config.max_retries})")
                response = self.llm.invoke(messages)

        if not response:
             msg = f"[{request_id}] No response received from LLM."
             raise SummarizationError(msg)

        return response

    def _process_response(self, response: BaseMessage, request_id: str) -> str:
        """Helper to process LLM response content."""
        content: str | list[str | dict[str, Any]] = response.content

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            logger.warning(f"[{request_id}] Received list content from LLM: {content}")
            return " ".join([str(c) for c in content])

        logger.warning(f"[{request_id}] Received unexpected content type from LLM: {type(content)}")
        return str(content)
