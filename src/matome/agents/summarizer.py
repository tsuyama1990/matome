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

    def __init__(self, config: ProcessingConfig, llm: ChatOpenAI | None = None) -> None:
        """
        Initialize the SummarizationAgent.

        Args:
            config: Processing configuration containing model name, retries, etc.
            llm: Optional pre-configured LLM instance. If None, it will be initialized from config.
        """
        self.config = config
        self.model_name = config.summarization_model

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
        strategy: PromptStrategy | None = None,
    ) -> str:
        """
        Summarize the provided text using the Chain of Density strategy.

        Args:
            text: The text to summarize.
            config: Optional config override. Uses self.config if None.
            strategy: Optional summarization strategy. Defaults to BaseSummaryStrategy (Chain of Density).
        """
        effective_config = config or self.config
        # Use provided strategy or default
        effective_strategy = strategy or BaseSummaryStrategy()

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
            preview = safe_text if isinstance(safe_text, str) else safe_text[0]
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
            # Use Strategy to format prompt
            prompt_str = effective_strategy.format_prompt(safe_text)
            messages = [HumanMessage(content=prompt_str)]

            response = self._invoke_llm(messages, effective_config, request_id)
            response_text = self._process_response(response, request_id)

            # Use Strategy to parse output
            parsed_output = effective_strategy.parse_output(response_text)

            # Return the summary part.
            # BaseSummaryStrategy returns {"summary": text}.
            # If strategy returns dict without summary key, fallback to raw text?
            # Or raise error? For now, fallback to raw text if empty.
            return str(parsed_output.get("summary", response_text))

        except Exception as e:
            logger.exception(f"[{request_id}] Summarization failed for text length {len(text)}")
            msg = f"Summarization failed: {e}"
            raise SummarizationError(msg) from e

    def _validate_input(
        self, text: str | list[str], max_input_length: int, max_word_length: int
    ) -> None:
        """
        Sanitize and validate input text.

        Checks:
        1. Maximum overall length to prevent processing extremely large inputs.
        2. Control characters (Unicode 'C' category).
        3. Word length to prevent tokenizer Denial of Service (DoS) attacks.

        Args:
            text: The input text to validate (str or list[str]).
            max_input_length: Maximum allowed total characters.
            max_word_length: The maximum allowed length for a single word.

        Raises:
            ValueError: If any validation check fails.
        """
        if isinstance(text, str):
            self._validate_single_string(text, max_input_length, max_word_length)
        else:
            total_length = sum(len(t) for t in text)
            if total_length > max_input_length:
                msg = f"Input text exceeds maximum allowed length ({max_input_length} characters)."
                raise ValueError(msg)
            for t in text:
                self._validate_single_string(t, max_input_length, max_word_length)

    def _validate_single_string(
        self, text: str, max_input_length: int, max_word_length: int
    ) -> None:
        """Helper to validate a single string."""
        if len(text) > max_input_length:
            msg = f"Input text exceeds maximum allowed length ({max_input_length} characters)."
            raise ValueError(msg)

        allowed_controls = {"\n", "\t", "\r"}
        for char in text:
            if unicodedata.category(char).startswith("C") and char not in allowed_controls:
                msg = f"Input text contains invalid control character: {char!r} (U+{ord(char):04X})"
                raise ValueError(msg)

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

        Args:
            text: The input text to sanitize.

        Returns:
            The sanitized text string or list.
        """
        if isinstance(text, str):
            return self._sanitize_single_string(text)
        return [self._sanitize_single_string(t) for t in text]

    def _sanitize_single_string(self, text: str) -> str:
        """Helper to sanitize a single string."""
        # Normalize unicode to avoid bypasses using equivalent characters
        sanitized = unicodedata.normalize("NFKC", text)
        for pattern in PROMPT_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, "[Filtered]", sanitized)
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
            wait=wait_exponential(multiplier=1, min=2, max=10),
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
