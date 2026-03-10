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
    # Testing missing or malformed prefix.
    # API key structure validation ensures keys conform to expected vendor patterns, reducing the attack surface
    # against blind injection of random strings into downstream auth components.
    with pytest.raises(
        ValueError,
        match="API Key format is invalid. It must start with 'sk-or-v1-' followed by alphanumeric characters.",
    ):
        validate_api_key_format("invalid-prefix-that-is-long-enough-to-pass-length-check")


def test_validate_api_key_format_special_characters() -> None:
    # Keys should only contain alphanumeric characters after the prefix to prevent injection vectors.
    with pytest.raises(
        ValueError,
        match="API Key format is invalid. It must start with 'sk-or-v1-' followed by alphanumeric characters.",
    ):
        validate_api_key_format("sk-or-v1-invalid!@#key$with^special*chars")


def test_validate_api_key_format_entropy() -> None:
    # Keys with very low entropy (e.g., repeating the same character) are insecure
    # and likely placeholders, so they must be explicitly rejected.
    with pytest.raises(
        ValueError,
        match="API Key format is invalid. Key entropy is too low, indicating a potentially fake or compromised key.",
    ):
        validate_api_key_format("sk-or-v1-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")


def test_validate_api_key_format_boundaries() -> None:
    # Key must be within strict length bounds to prevent buffer overflows or denial of service
    # via massive payload injections.

    # Exactly 256 characters (valid) - using high entropy charset to pass entropy check
    import random
    import string

    chars = string.ascii_letters + string.digits
    random.seed(42)
    valid_suffix_len_max = 256 - len("sk-or-v1-")
    valid_max_key = "sk-or-v1-" + "".join(random.choices(chars, k=valid_suffix_len_max))
    assert validate_api_key_format(valid_max_key) == valid_max_key

    # Exactly 30 characters (valid)
    valid_suffix_len_min = 30 - len("sk-or-v1-")
    valid_min_key = "sk-or-v1-" + "".join(random.choices(chars, k=valid_suffix_len_min))
    assert validate_api_key_format(valid_min_key) == valid_min_key

    # Exceeding 256 characters (invalid)
    with pytest.raises(ValueError, match="API Key must be between 30 and 256 characters long."):
        validate_api_key_format(valid_max_key + "a")


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
