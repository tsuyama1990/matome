"""
Summarization Agent module.
This module implements the summarization logic using OpenRouter and Chain of Density prompting.
"""
import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from domain_models.config import ProcessingConfig
from matome.config import get_openrouter_api_key

logger = logging.getLogger(__name__)

# Chain of Density Prompt Template
COD_TEMPLATE = """
The following are chunks of text from a larger document, grouped by topic:
{context}

Please generate a high-density summary following these steps:
1. Create an initial summary (~400 chars).
2. Identify missing entities (names, numbers, terms) from the source.
3. Rewrite the summary to include these entities without increasing length.
4. Repeat 3 times.
Output ONLY the final, densest summary.
"""


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
                max_retries=3,
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
            raise ValueError(msg)

        prompt = COD_TEMPLATE.format(context=text)
        logger.debug(f"[{request_id}] Starting summarization for text length {len(text)}")

        try:
            # We use invoke directly. ChatOpenAI handles retries if configured.
            # But we can also wrap it in tenacity if we want more control or if
            # ChatOpenAI's internal retry isn't enough for some errors.
            # Given spec asks for retry logic, and we configured max_retries=3 in init,
            # that satisfies the requirement for "transient API failures".

            response = self.llm.invoke([HumanMessage(content=prompt)])

            # Add debug logging for successful response (Auditor suggestion)
            logger.debug(f"[{request_id}] Received response from LLM.")

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

        except Exception:
            # Enhanced error logging (Auditor suggestion)
            logger.exception(f"[{request_id}] Summarization failed for text length {len(text)}")
            raise
