import pytest

from src.domain_models.secure_string import SecureString


def test_secure_string_lifecycle() -> None:
    value = "super_secret_key"

    with SecureString(value) as secure_str:
        # Before exit, we can get value
        assert secure_str.get_value() == value

    # After exit, it should be zeroized and raise an error
    with pytest.raises(
        ValueError, match="SecureString has already been zeroized or context exited."
    ):
        secure_str.get_value()


def test_secure_string_explicit_zeroize() -> None:
    secure_str = SecureString("test_secret")
    assert secure_str.get_value() == "test_secret"

    secure_str.zeroize()
    with pytest.raises(
        ValueError, match="SecureString has already been zeroized or context exited."
    ):
        secure_str.get_value()
