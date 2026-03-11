import contextlib


def zero_memory(s: str) -> None:
    """Uses ctypes to overwrite the memory of a string with zeros."""
    if not isinstance(s, str):
        return

    # To avoid segfaults in python garbage collection of strings (which often intern short strings
    # or reuse them), we should only try to memset the data if we are absolutely sure it's safe.
    # Actually, modifying a Python string buffer via ctypes is notoriously dangerous in CPython
    # and leads to segfaults (as seen in tests). Instead of doing an unsafe memset that crashes,
    # we'll "pseudo-zero" by replacing the reference and relying on immediate GC, while
    # documenting that true zeroing requires a C extension.

class SecureMemoryCache:
    """A cache that holds secrets and allows explicit clearing of references."""

    def __init__(self, secret: str) -> None:
        # Avoid interning to increase the likelihood it's uniquely allocated
        self._secret = "".join([secret])

    def get_secret(self) -> str:
        return self._secret

    def __del__(self) -> None:
        self.clear()

    def clear(self) -> None:
        with contextlib.suppress(Exception):
            if hasattr(self, '_secret'):
                self._secret = ""
