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
from pydantic import SecretStr
from tenacity import Retrying, stop_after_attempt, wait_exponential

from domain_models.config import ProcessingConfig
from domain_models.constants import PROMPT_INJECTION_PATTERNS
from matome.agents.strategies import BaseSummaryStrategy
from matome.config import get_openrouter_api_key, get_openrouter_base_url
from matome.exceptions import SummarizationError
from matome.interfaces import PromptStrategy

logger = logging.getLogger(__name__)


class SummarizationAgent:
    """
    Agent responsible for summarizing text using an LLM.
    """

    def __init__(
        self,
        config: ProcessingConfig,
        llm: ChatOpenAI | None = None,
        strategy: PromptStrategy | None = None,
    ) -> None:
        """
        Initialize the SummarizationAgent.

        Args:
            config: Processing configuration containing model name, retries, etc.
            llm: Optional pre-configured LLM instance. If None, it will be initialized from config.
            strategy: Optional prompt generation strategy. Defaults to BaseSummaryStrategy.
        """
        self.config = config
        self.model_name = config.summarization_model
        self.strategy = strategy or BaseSummaryStrategy()

        # Determine API key and Base URL
        api_key = get_openrouter_api_key()
        base_url = get_openrouter_base_url()

        self.mock_mode = api_key == "mock"

        self.llm: ChatOpenAI | None = None

        if llm:
            self.llm = llm
            # If LLM is injected, we disable internal mock mode unless explicitly set via api_key="mock"
            # But the caller provided an LLM, so they probably want to use it.
            # If api_key is "mock", we might still want to short-circuit.
        elif api_key and not self.mock_mode:
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=SecretStr(api_key),
                base_url=base_url,
                temperature=config.llm_temperature,
                max_retries=config.max_retries,
            )
        else:
            self.llm = None

    def summarize(
        self,
        text: str | list[str],
        config: ProcessingConfig | None = None,
        level: int = 0,
        strategy: PromptStrategy | None = None,
    ) -> str:
        """
        Summarize the provided text using the Chain of Density strategy.

        Args:
            text: The text to summarize. Can be a string or a list of strings.
            config: Optional config override. Uses self.config if None.
            level: The hierarchical level of the summary.
            strategy: Optional strategy to override the default.
        """
        effective_config = config or self.config
        effective_strategy = strategy or self.strategy
        request_id = str(uuid.uuid4())

        if not text:
            logger.debug(f"[{request_id}] Skipping empty text summarization.")
            return ""

        # Validate input for security
        self._validate_input(
            text, effective_config.max_input_length, effective_config.max_word_length
        )

        # Sanitize prompt injection
        safe_text = self._sanitize_prompt_injection(text)

        if self.mock_mode:
            logger.info(f"[{request_id}] Mock mode enabled. Returning static summary.")
            preview = safe_text if isinstance(safe_text, str) else str(safe_text)
            return f"Summary of {preview[:20]}..."

        if not self.llm:
            msg = f"[{request_id}] LLM not initialized (missing API Key?). Cannot perform summarization."
            logger.error(msg)
            raise SummarizationError(msg)

        if effective_config.summarization_model != self.model_name:
            logger.debug(
                f"[{request_id}] Config model {effective_config.summarization_model} differs from agent model {self.model_name}. Using agent model."
            )

        try:
            # Create prompt using the strategy
            # The strategy should handle str or list[str]
            prompt = effective_strategy.create_prompt(safe_text, context={"level": level})
            messages = [HumanMessage(content=prompt)]

            response = self._invoke_llm(messages, effective_config, request_id)
            return self._process_response(response, request_id)

        except Exception as e:
            text_len = len(text) if isinstance(text, str) else sum(len(t) for t in text)
            logger.exception(f"[{request_id}] Summarization failed for text length {text_len}")
            msg = f"Summarization failed: {e}"
            raise SummarizationError(msg) from e

    def _validate_input(
        self, text: str | list[str], max_input_length: int, max_word_length: int
    ) -> None:
        """
        Sanitize and validate input text.
        Handles both single string and list of strings.
        """
        if isinstance(text, list):
            total_len = sum(len(t) for t in text)
            if total_len > max_input_length:
                msg = f"Input text (combined) exceeds maximum allowed length ({max_input_length} characters)."
                raise ValueError(msg)
            for t in text:
                self._validate_single_text_content(t, max_word_length)
        else:
            if len(text) > max_input_length:
                msg = f"Input text exceeds maximum allowed length ({max_input_length} characters)."
                raise ValueError(msg)
            self._validate_single_text_content(text, max_word_length)

    def _validate_single_text_content(self, text: str, max_word_length: int) -> None:
        """
        Validates content of a single text string: control chars and word length.
        """
        # Control Character Check (Unicode)
        allowed_controls = {"\n", "\t"}
        for char in text:
            if unicodedata.category(char).startswith("C") and char not in allowed_controls:
                msg = f"Input text contains invalid control character: {char!r} (U+{ord(char):04X})"
                raise ValueError(msg)

        # Tokenizer DoS Protection
        words = text.split()
        if not words:
            return

        longest_word_len = max((len(w) for w in words), default=0)
        if longest_word_len > max_word_length:
            msg = f"Input text contains extremely long words (>{max_word_length} chars) - potential DoS vector."
            raise ValueError(msg)

    def _sanitize_prompt_injection(self, text: str | list[str]) -> str | list[str]:
        """
        Basic mitigation for Prompt Injection.
        Handles both single string and list of strings.
        """
        if isinstance(text, list):
            return [self._sanitize_single_text(t) for t in text]
        return self._sanitize_single_text(text)

    def _sanitize_single_text(self, text: str) -> str:
        """
        Sanitizes a single text string.
        """
        sanitized = text
        for pattern in PROMPT_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, "[Filtered]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def _invoke_llm(
        self, messages: list[HumanMessage], config: ProcessingConfig, request_id: str
    ) -> BaseMessage:
        """
        Invoke the LLM with exponential backoff retry logic.

        Args:
            messages: List of LangChain messages to send.
            config: Configuration containing retry settings.
            request_id: Unique ID for logging purposes.

        Returns:
            The response message from the LLM.

        Raises:
            SummarizationError: If the LLM call fails after all retries or returns no response.
        """
        if not self.llm:
            msg = "LLM not initialized"
            raise SummarizationError(msg)

        response = None
        # Use Tenacity for retries based on config
        for attempt in Retrying(
            stop=stop_after_attempt(config.max_retries),
            wait=wait_exponential(
                multiplier=config.retry_multiplier,
                min=config.retry_min_wait,
                max=config.retry_max_wait,
            ),
            reraise=True,
        ):
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    logger.warning(
                        f"[{request_id}] Retrying LLM call (Attempt {attempt.retry_state.attempt_number}/{config.max_retries})"
                    )

                # Check if LLM is chat model or simple LLM (though typed as ChatOpenAI)
                if hasattr(self.llm, "invoke"):
                    response = self.llm.invoke(messages)
                else:
                    # Fallback for mock objects that might not have invoke
                    response = self.llm(messages)  # type: ignore[operator]

        if not response:
            msg = f"[{request_id}] No response received from LLM."
            raise SummarizationError(msg)

        return response

    def _process_response(self, response: BaseMessage, request_id: str) -> str:
        """
        Process and extract content from the LLM response.

        Handles different response types (string, list, etc.) and ensures a string return.

        Args:
            response: The raw response message from the LLM.
            request_id: Unique ID for logging.

        Returns:
            The extracted summary text.
        """
        content: str | list[str | dict[str, Any]] = response.content

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            logger.warning(f"[{request_id}] Received list content from LLM: {content}")
            return " ".join([str(c) for c in content])

        logger.warning(f"[{request_id}] Received unexpected content type from LLM: {type(content)}")
        return str(content)
