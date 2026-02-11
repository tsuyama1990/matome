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
from tenacity import Retrying, stop_after_attempt, wait_exponential

from domain_models.config import ProcessingConfig
from domain_models.constants import PROMPT_INJECTION_PATTERNS
from matome.agents.strategies import BaseSummaryStrategy, PromptStrategy
from matome.config import get_openrouter_api_key, get_openrouter_base_url
from matome.exceptions import SummarizationError

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
            strategy: Optional prompt strategy. Defaults to BaseSummaryStrategy (CoD).
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
                api_key=api_key,
                base_url=base_url,
                temperature=config.llm_temperature,
                max_retries=config.max_retries,
            )
        else:
            self.llm = None

    def summarize(self, text: str, config: ProcessingConfig | None = None) -> str:
        """
        Summarize the provided text using the configured strategy.

        Args:
            text: The text to summarize.
            config: Optional config override. Uses self.config if None.
        """
        effective_config = config or self.config
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
            return f"Summary of {safe_text[:20]}..."

        if not self.llm:
            msg = f"[{request_id}] LLM not initialized (missing API Key?). Cannot perform summarization."
            logger.error(msg)
            raise SummarizationError(msg)

        if effective_config.summarization_model != self.model_name:
            logger.debug(
                f"[{request_id}] Config model {effective_config.summarization_model} differs from agent model {self.model_name}. Using agent model."
            )

        try:
            prompt = self.strategy.generate_prompt(safe_text)
            messages = [HumanMessage(content=prompt)]

            response = self._invoke_llm(messages, effective_config, request_id)
            processed = self._process_response(response, request_id)
            return self.strategy.parse_response(processed)

        except Exception as e:
            logger.exception(f"[{request_id}] Summarization failed for text length {len(text)}")
            msg = f"Summarization failed: {e}"
            raise SummarizationError(msg) from e

    def _validate_input(self, text: str, max_input_length: int, max_word_length: int) -> None:
        """
        Sanitize and validate input text.

        Checks:
        1. Maximum overall length to prevent processing extremely large inputs.
        2. Control characters (Unicode 'C' category).
           We strictly disallow control characters that are not standard whitespace.
           While Newline (\\n) and Tab (\\t) are often used for formatting, they can be used for injection.
           However, blocking them makes summarizing documents impossible.
           Therefore, we strictly validate that ONLY \\n and \\t are present among control chars.
           Other control characters (like \\r, null bytes, backspaces) are rejected.
        3. Word length to prevent tokenizer Denial of Service (DoS) attacks.

        Args:
            text: The input text to validate.
            max_input_length: Maximum allowed total characters.
            max_word_length: The maximum allowed length for a single word.

        Raises:
            ValueError: If any validation check fails.
        """
        # 1. Length Check (Document)
        if len(text) > max_input_length:
            msg = f"Input text exceeds maximum allowed length ({max_input_length} characters)."
            raise ValueError(msg)

        # 2. Control Character Check (Unicode)
        # We strictly disallow control characters that are not standard whitespace.
        # Allow standard whitespace controls: \n, \t, \r
        # \f and \v are technically whitespace but rare, safer to block if not needed?
        # Let's align with common definition: \t, \n, \r.
        allowed_controls = {"\n", "\t", "\r"}

        for char in text:
            # Check for control characters (Cc, Cf, Cs, Co, Cn)
            if unicodedata.category(char).startswith("C") and char not in allowed_controls:
                msg = f"Input text contains invalid control character: {char!r} (U+{ord(char):04X})"
                raise ValueError(msg)

        # 3. Tokenizer DoS Protection
        # Split by whitespace to check word length
        words = text.split()
        if not words:
            return

        longest_word_len = max((len(w) for w in words), default=0)
        if longest_word_len > max_word_length:
            msg = f"Input text contains extremely long words (>{max_word_length} chars) - potential DoS vector."
            raise ValueError(msg)

    def _sanitize_prompt_injection(self, text: str) -> str:
        """
        Basic mitigation for Prompt Injection.

        Iterates through a list of known injection patterns (e.g., 'ignore previous instructions')
        and replaces them with a placeholder '[Filtered]'.

        Using literal string matching (if pattern is simple) or careful regex matching
        is handled by PROMPT_INJECTION_PATTERNS definitions.

        Args:
            text: The input text to sanitize.

        Returns:
            The sanitized text string.
        """
        sanitized = text
        for pattern in PROMPT_INJECTION_PATTERNS:
            # We use re.sub for flexible matching (case insensitive, whitespace variations)
            # which are defined in the patterns themselves.
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
