"""
Summarization Agent module.
This module implements the summarization logic using OpenRouter and Chain of Density prompting.
"""
import logging
import re
import unicodedata
import uuid
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from tenacity import stop_after_attempt, wait_exponential

from domain_models.config import ProcessingConfig
from matome.config import get_openrouter_api_key, get_openrouter_base_url
from matome.exceptions import SummarizationError
from matome.utils.prompts import COD_TEMPLATE

logger = logging.getLogger(__name__)


class SummarizationAgent:
    """
    Agent responsible for summarizing text using an LLM.
    """

    def __init__(self, config: ProcessingConfig) -> None:
        """
        Initialize the SummarizationAgent.

        Args:
            config: Processing configuration containing model name, retries, etc.
        """
        # Retrieve API key securely from environment via config utility
        api_key = get_openrouter_api_key()
        base_url = get_openrouter_base_url()

        # Determine model name
        self.model_name = config.summarization_model

        self.api_key = api_key
        self.llm: ChatOpenAI | None = None

        # Initialize LLM only if API key is present (or if we want to allow failure later)
        # Check for 'mock' value explicitly to enable testing mode without real calls
        if api_key and api_key != "mock":
            # langchain_openai handles retries internally if max_retries > 0,
            # but we also wrap calls with tenacity for more control if needed.
            # Here we set max_retries to 0 in the client to let tenacity handle it,
            # or we rely on the client. Let's use config.max_retries in client.
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=config.llm_temperature,
                max_retries=config.max_retries,
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
        self._validate_input(text, config.max_word_length)

        # Sanitize prompt injection
        safe_text = self._sanitize_prompt_injection(text)

        # Mock Mode Check
        if self.api_key == "mock":
            logger.info(f"[{request_id}] Mock mode enabled. Returning static summary.")
            return f"Summary of {safe_text[:20]}..."

        if not self.llm:
            msg = f"[{request_id}] OpenRouter API Key is missing. Cannot perform summarization."
            logger.error(msg)
            raise SummarizationError(msg)

        if config.summarization_model != self.model_name:
             logger.debug(f"[{request_id}] Config model {config.summarization_model} differs from agent model {self.model_name}. Using agent model.")

        try:
            prompt = COD_TEMPLATE.format(context=safe_text)
            messages = [HumanMessage(content=prompt)]

            response = self._invoke_llm(messages, config, request_id)
            return self._process_response(response, request_id)

        except Exception as e:
            # Enhanced error logging with custom exception
            logger.exception(f"[{request_id}] Summarization failed for text length {len(text)}")
            msg = f"Summarization failed: {e}"
            raise SummarizationError(msg) from e

    def _validate_input(self, text: str, max_word_length: int) -> None:
        """
        Sanitize and validate input text to prevent injection attacks or excessive load.
        """
        # 1. Length Check
        MAX_INPUT_LENGTH = 500_000
        if len(text) > MAX_INPUT_LENGTH:
             msg = f"Input text exceeds maximum allowed length ({MAX_INPUT_LENGTH} characters)."
             raise ValueError(msg)

        # 2. Control Character Check (Unicode)
        # Iterate and check category of each character.
        # Categories: Cc (Control), Cf (Format), Cs (Surrogate), Co (Private Use), Cn (Unassigned)
        # We allow newlines/tabs which are Cc but usually safe/needed for formatting.
        # Allow: \n (0x0A), \r (0x0D), \t (0x09)
        allowed_controls = {"\n", "\r", "\t"}

        for char in text:
            if unicodedata.category(char).startswith("C") and char not in allowed_controls:
                 msg = f"Input text contains invalid control character: {char!r}"
                 raise ValueError(msg)

        # 3. Tokenization DoS Protection (Long words)
        # Check for extremely long uninterrupted sequences which can cause tokenizer issues
        # Using a generator expression to be memory efficient
        longest_word_len = max((len(w) for w in text.split()), default=0)
        if longest_word_len > max_word_length:
             msg = f"Input text contains extremely long words (>{max_word_length} chars) - potential DoS vector."
             raise ValueError(msg)

    def _sanitize_prompt_injection(self, text: str) -> str:
        """
        Basic mitigation for Prompt Injection.
        Escapes or removes sequences that might confuse the LLM or break out of the context block.
        """
        # Remove explicit "Ignore previous instructions" patterns
        # Simple regex for common jailbreaks
        patterns = [
            r"(?i)ignore\s+previous\s+instructions",
            r"(?i)system\s+override",
            r"(?i)ignore\s+all\s+instructions",
        ]

        sanitized = text
        for pattern in patterns:
            sanitized = re.sub(pattern, "[Filtered]", sanitized)

        return sanitized

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
