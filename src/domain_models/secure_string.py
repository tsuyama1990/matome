import ctypes
from typing import Self


class SecureString:
    def __init__(self, value: str) -> None:
        self._data: bytearray | None = bytearray(value.encode("utf-8", "strict"))
        self._length: int = len(self._data)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._data is not None:
            # Overwrite the bytearray data with zeros in memory safely without corrupting the interpreter
            buffer = (ctypes.c_char * self._length).from_buffer(self._data)
            ctypes.memset(ctypes.addressof(buffer), 0, self._length)
            self._data = None
            self._length = 0
