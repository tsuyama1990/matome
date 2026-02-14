"""
Summarization Agent module.
This module implements the summarization logic using OpenRouter and Chain of Density prompting.
"""

import base64
import logging
import re
import unicodedata
import urllib.parse
import uuid
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from tenacity import Retrying, stop_after_attempt, wait_exponential

from domain_models.config import ProcessingConfig
from domain_models.constants import PROMPT_INJECTION_PATTERNS, SYSTEM_INJECTION_PATTERNS
from matome.agents.strategies import ChainOfDensityStrategy
from matome.config import get_openrouter_api_key, get_openrouter_base_url
from matome.exceptions import SummarizationError
from matome.interfaces import PromptStrategy

logger = logging.getLogger(__name__)


class SummarizationAgent:
    """
    Agent responsible for summarizing text using an LLM.
    """

    llm: ChatOpenAI | None
    config: ProcessingConfig
    model_name: str
    mock_mode: bool

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

        self.llm = None

        if llm:
            self.llm = llm
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

    def summarize(
        self,
        text: str,
        config: ProcessingConfig | None = None,
        strategy: PromptStrategy | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Summarize the provided text using the specified strategy (or default Chain of Density).

        Args:
            text: The text to summarize.
            config: Optional config override. Uses self.config if None.
            strategy: Optional PromptStrategy. Defaults to ChainOfDensityStrategy (Chain of Density).
            context: Optional context dictionary to pass to the strategy (e.g. user instructions).
        """
        effective_config = config or self.config
        effective_strategy = strategy or ChainOfDensityStrategy()
        request_id = str(uuid.uuid4())

        if effective_strategy and not isinstance(effective_strategy, PromptStrategy):
            msg = f"Invalid strategy type: {type(effective_strategy)}. Must be an instance of PromptStrategy."
            raise ValueError(msg)

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
            # We don't re-init LLM here as it's expensive, but log warning if significant mismatch
            pass

        try:
            # Construct prompt using strategy
            prompt_content = effective_strategy.format_prompt(safe_text, context)
            messages = [HumanMessage(content=prompt_content)]

            response = self._invoke_llm(messages, effective_config, request_id)
            return self._process_response(response, request_id)

        except Exception as e:
            logger.exception(f"[{request_id}] Summarization failed for text length {len(text)}")
            msg = f"Summarization failed: {e}"
            raise SummarizationError(msg) from e

    def _validate_input(self, text: str, max_input_length: int, max_word_length: int) -> None:
        """
        Sanitize and validate input text.
        Raises ValueError if validation fails.
        """
        self._check_length(text, max_input_length)
        self._check_control_chars(text, max_input_length)
        self._check_dos_vectors(text, max_word_length)
        self._check_injection_patterns(text)

    def _check_length(self, text: str, max_input_length: int) -> None:
        """Check document length."""
        if len(text) > max_input_length:
            msg = f"Input text exceeds maximum allowed length ({max_input_length} characters)."
            raise ValueError(msg)

    def _check_control_chars(self, text: str, max_input_length: int) -> None:
        """Check for invalid control characters and unicode normalization."""
        # Security: Normalize unicode to prevent homograph/normalization attacks
        normalized_text = unicodedata.normalize("NFKC", text)
        if len(normalized_text) != len(text) and len(normalized_text) > max_input_length:
            msg = "Normalized text exceeds maximum length."
            raise ValueError(msg)

        allowed_controls = {"\n", "\t", "\r"}
        for char in normalized_text:
            if unicodedata.category(char).startswith("C") and char not in allowed_controls:
                msg = f"Input text contains invalid control character: {char!r} (U+{ord(char):04X})"
                raise ValueError(msg)

    def _check_dos_vectors(self, text: str, max_word_length: int) -> None:
        """Check for tokenizer DoS vectors (extremely long words)."""
        words = text.split()
        if not words:
            return
        longest_word_len = max((len(w) for w in words), default=0)
        if longest_word_len > max_word_length:
            msg = f"Input text contains extremely long words (>{max_word_length} chars) - potential DoS vector."
            raise ValueError(msg)

    def _check_injection_patterns(self, text: str) -> None:
        """Check for prompt and system command injection patterns."""

        # Helper to check a string against patterns
        def check(s: str) -> None:
            # 4. Prompt Injection Check
            for pattern in PROMPT_INJECTION_PATTERNS:
                if re.search(pattern, s, flags=re.IGNORECASE | re.MULTILINE):
                    msg = f"Potential prompt injection detected: {pattern}"
                    raise ValueError(msg)

            # 5. SQL/System Injection Check
            for pattern in SYSTEM_INJECTION_PATTERNS:
                if re.search(pattern, s, flags=re.IGNORECASE | re.MULTILINE):
                    msg = f"Input text contains suspicious pattern (SQL/Command Injection): {pattern}"
                    raise ValueError(msg)

        # Check original text
        check(text)

        # Check URL encoded
        try:
            decoded_url = urllib.parse.unquote(text)
            if decoded_url != text:
                check(decoded_url)
        except Exception:
            pass

        # Check Base64 encoded (heuristic: if it looks like base64, try decoding)
        # We only check if the whole string is base64 or significant chunks?
        # For simplicity, if the text is valid base64, check the decoded content.
        # This is a basic check.
        if len(text) > 10 and len(text) % 4 == 0 and re.match(r'^[A-Za-z0-9+/]+={0,2}$', text):
            try:
                decoded_b64 = base64.b64decode(text, validate=True).decode('utf-8', errors='ignore')
                check(decoded_b64)
            except Exception:
                pass

    def _sanitize_prompt_injection(self, text: str) -> str:
        """
        Basic mitigation for Prompt Injection.
        Replaces known injection patterns with '[Filtered]'.
        """
        sanitized = text
        for pattern in PROMPT_INJECTION_PATTERNS:
            # Use re.sub with compiled pattern if possible, or just flags
            # Ensure we catch variations
            sanitized = re.sub(pattern, "[Filtered]", sanitized, flags=re.IGNORECASE)

        # Validate length after sanitization just in case replacement significantly increases size
        # (unlikely with [Filtered], but good practice)
        if len(sanitized) > self.config.max_input_length:
             msg = "Sanitized text exceeds maximum length."
             raise ValueError(msg)

        return sanitized

    def _invoke_llm(
        self, messages: list[HumanMessage], config: ProcessingConfig, request_id: str
    ) -> BaseMessage:
        """
        Invoke the LLM with exponential backoff retry logic.
        Handles API errors and retries according to config.
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

                if hasattr(self.llm, "invoke"):
                    response = self.llm.invoke(messages)
                else:
                    response = self.llm(messages)  # type: ignore[operator]

        if not response:
            msg = f"[{request_id}] No response received from LLM."
            raise SummarizationError(msg)

        return response

    def _process_response(self, response: BaseMessage, request_id: str) -> str:
        """
        Process and extract content from the LLM response.
        """
        content: str | list[str | dict[str, Any]] = response.content

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            logger.warning(f"[{request_id}] Received list content from LLM: {content}")
            return " ".join([str(c) for c in content])

        logger.warning(f"[{request_id}] Received unexpected content type from LLM: {type(content)}")
        return str(content)
