import pytest

from src.utils.validation import validate_api_key_format


def test_validate_api_key_format_none() -> None:
    with pytest.raises(ValueError, match="API Key cannot be empty."):
        validate_api_key_format(None)


def test_validate_api_key_format_empty() -> None:
    with pytest.raises(ValueError, match="API Key cannot be empty."):
        validate_api_key_format("")


def test_validate_api_key_format_too_short() -> None:
    with pytest.raises(ValueError, match="API Key must be between 30 and 256 characters long."):
        validate_api_key_format("sk-or-v1-short")


def test_validate_api_key_format_invalid_prefix() -> None:
    with pytest.raises(
        ValueError,
        match="API Key format is invalid. It must start with 'sk-or-v1-' followed by alphanumeric characters.",
    ):
        validate_api_key_format("invalid-prefix-that-is-long-enough-to-pass-length-check")


def test_validate_api_key_format_valid() -> None:
    valid_key = "sk-or-v1-thisisavalidkeythatislongenough"
    assert validate_api_key_format(valid_key) == valid_key


def test_credential_error_handler_invalid_type() -> None:
    from src.utils.errors import CredentialErrorHandler
    from src.domain_models.exceptions import ConfigurationError

    handler = CredentialErrorHandler()
    with pytest.raises(ConfigurationError, match="Incorrect data type provided"):
        handler.handle_invalid_type()


def test_credential_error_handler_validate_and_format_exception() -> None:
    from src.utils.errors import CredentialErrorHandler
    from src.domain_models.exceptions import ConfigurationError

    handler = CredentialErrorHandler()
    with pytest.raises(ConfigurationError, match="API Key validation failed"):
        # Passing an explicitly invalid format key to trigger the ValueError internally
        handler.validate_and_format("short_key")
