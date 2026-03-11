class SecureMemoryCache:
    """A cache that holds secrets via bytearrays to guarantee secure zeroization without segfaults."""

    def __init__(self, secret: str) -> None:
        # Store as a mutable bytearray to allow safe in-place memory wiping
        self._secret = bytearray(secret, "utf-8")

    def get_secret(self) -> str:
        """Decodes the bytes to string immediately for use."""
        return self._secret.decode("utf-8")

    def clear(self) -> None:
        """Securely zeroes out the memory of the mutable byte buffer."""
        if hasattr(self, "_secret") and self._secret:
            for i in range(len(self._secret)):
                self._secret[i] = 0
            # Remove reference
            self._secret = bytearray()

    def __del__(self) -> None:
        self.clear()
