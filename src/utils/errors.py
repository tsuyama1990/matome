import logging
import typing

logger = logging.getLogger(__name__)

class CredentialErrorHandler:
    """Handles parsing errors and format validation specifically for credentials securely without logging specifics."""

    def handle_missing_key(self) -> typing.NoReturn:
        from src.domain_models.exceptions import ConfigurationError

        logger.warning(
            "API Key validation failed: Required API Key is missing from the environment.",
            extra={"context": "auth"},
        )
        msg = "API Key validation failed: The key is entirely missing. Please check your environment variables."
        raise ConfigurationError(msg)

    def handle_invalid_type(self) -> typing.NoReturn:
        from src.domain_models.exceptions import ConfigurationError

        logger.warning(
            "API Key validation failed: The provided key is not a string.",
            extra={"context": "auth"},
        )
        msg = "API Key validation failed: Incorrect data type provided."
        raise ConfigurationError(msg)

    def validate_and_format(self, key: str) -> None:
        from src.domain_models.exceptions import ConfigurationError
        from src.infrastructure.security import DefaultSecurityService

        try:
            DefaultSecurityService().validate_api_key(key)
        except ValueError as err:
            logger.warning(
                "API Key validation failed during formatting/checks. Check permissions and input.",
                extra={"context": "auth"},
            )
            msg = f"API Key validation failed: {err!s} Please check your key format and permissions."
            raise ConfigurationError(msg) from err
