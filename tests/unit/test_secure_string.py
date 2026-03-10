from src.domain_models.secure_string import SecureString


def test_secure_string_zeroization() -> None:
    value_to_secure = "some_random_value_to_protect"

    with SecureString(value_to_secure) as secure_str:
        assert secure_str._data is not None
        assert secure_str._length == len(value_to_secure.encode("utf-8"))

        # Verify it stores the correct byte sequence internally
        assert secure_str._data == bytearray(value_to_secure.encode("utf-8"))

    # After exit, _data should be explicitly zeroized and set to None
    assert secure_str._data is None
    assert secure_str._length == 0
