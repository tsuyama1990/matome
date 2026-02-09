"""
Configuration module for the Matome system.
This module handles environment variables and system-wide settings that are not part of the domain model.
"""

import logging
import os

logger = logging.getLogger(__name__)


def get_openrouter_api_key() -> str | None:
    """
    Retrieve the OpenRouter API key from environment variables.

    Returns:
        The API key as a string if set, otherwise None.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY environment variable is not set.")
    return api_key


def get_openrouter_base_url() -> str:
    """
    Retrieve the OpenRouter Base URL from environment variables.

    Returns:
        The Base URL as a string. Defaults to "https://openrouter.ai/api/v1".
    """
    return os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
