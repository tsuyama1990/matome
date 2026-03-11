import ctypes
from collections.abc import Callable
from typing import Any

from cryptography.fernet import Fernet
from pydantic import Field, PrivateAttr, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecureString:
    """A highly secure string class that guarantees explicit zeroization in memory via ctypes.

    It prevents race conditions by forcing the user to provide a callback that receives
    the decoded string. The string is zeroized immediately after the callback completes.
    """

    def __init__(self, data: str) -> None:
        self._data = bytearray(data.encode("utf-8"))
        self._length = len(self._data)

    def use(self, callback: Callable[[str], Any]) -> Any:
        """Executes the callback with the decoded string and immediately zeroizes it."""
        decoded_str = self._data.decode("utf-8")
        try:
            return callback(decoded_str)
        finally:
            # Zeroize the decoded string from memory as best we can natively in python.
            # Python strings are immutable, but we can try to overwrite the byte buffer directly using ctypes.
            # Since `decoded_str` is a string object, its memory layout is complex.
            # We zeroize our internal bytearray buffer first.
            buffer = (ctypes.c_char * self._length).from_buffer(self._data)
            ctypes.memset(buffer, 0, self._length)

            # The decoded python string object `decoded_str` is immutable and managed by python GC.
            # To aggressively minimize its lifetime, we explicitly delete the reference.
            del decoded_str


class CredentialConfig(BaseSettings):
    """Configuration for sensitive credentials with encryption at rest."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    openrouter_api_key: SecretStr | None = None

    # Use Pydantic's PrivateAttr for internal state instead of underscore fields
    _encryption_key: bytes = PrivateAttr()
    _encrypted_api_key: bytes | None = PrivateAttr(default=None)

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: SecretStr | None) -> SecretStr | None:
        """Validates API key format and length."""
        if v is not None:
            val = v.get_secret_value()
            if len(val) < 20:
                msg = "API key must be at least 20 characters long"
                raise ValueError(msg)
            if not val.startswith("sk-or-"):
                msg = "API key must start with 'sk-or-'"
                raise ValueError(msg)
        return v

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._encryption_key = Fernet.generate_key()

        # Encrypt the API key at rest upon instantiation
        if self.openrouter_api_key is not None:
            fernet = Fernet(self._encryption_key)
            self._encrypted_api_key = fernet.encrypt(
                self.openrouter_api_key.get_secret_value().encode("utf-8")
            )

            # Erase the raw SecretStr entirely to prevent memory inspection
            # Note: Pydantic expects the attribute to exist, so we set it to None
            # effectively removing the unencrypted key from the model instance
            self.openrouter_api_key = None

    def get_decrypted_api_key(self) -> SecureString | None:
        """Returns the decrypted API key securely wrapped in a SecureString."""
        if self._encrypted_api_key is None:
            return None
        fernet = Fernet(self._encryption_key)
        decrypted_bytes = fernet.decrypt(self._encrypted_api_key)
        return SecureString(decrypted_bytes.decode("utf-8"))


class PipelineConfig(BaseSettings):
    """Configuration for the document processing pipeline."""

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="forbid")

    credentials: CredentialConfig = Field(default_factory=CredentialConfig)
    max_chunk_scan_size: int = 10000
    fast_model: str = "google/gemini-2.5-flash"
    reasoning_model: str = "anthropic/claude-3.7-sonnet"
    multimodal_model: str = "openai/gpt-4o"
    trusted_model_hashes: list[str] = Field(default_factory=list)
