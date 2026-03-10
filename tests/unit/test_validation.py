import pytest

from src.utils.validation import validate_api_key_format


def test_validate_api_key_format_none():
    assert validate_api_key_format(None) is None


def test_validate_api_key_format_empty():
    assert validate_api_key_format("") == ""


def test_validate_api_key_format_too_short():
    with pytest.raises(ValueError, match="API Key must be at least 30 characters long."):
        validate_api_key_format("sk-or-v1-short")


def test_validate_api_key_format_invalid_prefix():
    with pytest.raises(
        ValueError,
        match="API Key format is invalid. It must start with 'sk-or-v1-' followed by alphanumeric characters.",
    ):
        validate_api_key_format("invalid-prefix-that-is-long-enough-to-pass-length-check")


def test_validate_api_key_format_valid():
    valid_key = "sk-or-v1-thisisavalidkeythatislongenough"
    assert validate_api_key_format(valid_key) == valid_key
