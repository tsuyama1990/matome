"""
Summarization Agent module.
This module implements the summarization logic using OpenRouter and Chain of Density prompting.
"""
import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from tenacity import stop_after_attempt, wait_exponential

from domain_models.config import ProcessingConfig
from matome.config import get_openrouter_api_key
from matome.exceptions import SummarizationError
from matome.utils.prompts import COD_TEMPLATE

logger = logging.getLogger(__name__)


class SummarizationAgent:
    """
    Agent responsible for summarizing text using an LLM.
    """

    def __init__(self, model_name: str = "google/gemini-flash-1.5") -> None:
        """
        Initialize the SummarizationAgent.

        Args:
            model_name: The name of the model to use (default: google/gemini-flash-1.5).
        """
        api_key = get_openrouter_api_key()
        self.model_name = model_name
        self.api_key = api_key
        self.llm: ChatOpenAI | None = None

        # Initialize LLM only if API key is present (or if we want to allow failure later)
        if api_key and api_key != "mock":
            self.llm = ChatOpenAI(
                model=model_name,
                api_key=api_key,  # type: ignore[arg-type]
                base_url="https://openrouter.ai/api/v1",
                temperature=0,
                # We handle retries via tenacity wrapper now, but keeping internal retry low
                max_retries=1,
            )

    def summarize(self, text: str, config: ProcessingConfig) -> str:
        """
        Summarize the provided text using the Chain of Density strategy.

        Args:
            text: The text to summarize.
            config: Configuration parameters (currently unused by this specific implementation
                    but required by interface).

        Returns:
            The generated summary.

        Raises:
            SummarizationError: If summarization fails or API key is missing.
        """
        request_id = str(uuid.uuid4())

        if not text:
            logger.debug(f"[{request_id}] Skipping empty text summarization.")
            return ""

        # Mock Mode Check
        if self.api_key == "mock":
            logger.info(f"[{request_id}] Mock mode enabled. Returning static summary.")
            return f"Summary of {text[:20]}..."

        if not self.llm:
            msg = f"[{request_id}] OpenRouter API Key is missing. Cannot perform summarization."
            logger.error(msg)
            raise SummarizationError(msg)

        prompt = COD_TEMPLATE.format(context=text)
        logger.debug(f"[{request_id}] Prompt constructed. Starting LLM invocation for text length {len(text)}")

        messages = [HumanMessage(content=prompt)]

        try:
            # Call helper with retry logic
            # We configure retry dynamically based on config inside the helper if possible,
            # but tenacity decorators are static.
            # To respect config.max_retries, we can create a Retrying object or
            # use a simpler approach if the decorator is fixed.
            # For this cycle, using a fixed robust retry or one configured at class level is acceptable,
            # but ideally we respect the config passed in.

            # Since tenacity decorators are processed at definition time,
            # we will use the `Retrying` context manager or functional API inside the method
            # to allow dynamic configuration from `config`.

            from tenacity import Retrying

            response = None
            # Use tenacity Retrying context for dynamic configuration
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
                 raise SummarizationError(f"[{request_id}] No response received from LLM.")

            # Add debug logging for successful response
            logger.debug(f"[{request_id}] Received response from LLM. Processing content.")

            # response.content is usually str or list of blocks. For ChatOpenAI it's str.
            content: str | list[str | dict[str, Any]] = response.content

            if isinstance(content, str):
                return content
            if isinstance(content, list):
                # Handle potential list content (e.g. from some models)
                logger.warning(f"[{request_id}] Received list content from LLM: {content}")
                return " ".join([str(c) for c in content])

            # Fallback for unexpected types
            logger.warning(f"[{request_id}] Received unexpected content type from LLM: {type(content)}")
            return str(content)

        except Exception as e:
            # Enhanced error logging with custom exception
            logger.exception(f"[{request_id}] Summarization failed for text length {len(text)}")
            msg = f"Summarization failed: {e}"
            raise SummarizationError(msg) from e
