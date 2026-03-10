import ctypes
import typing


class SecureString:
    """
    A class that holds a sensitive string in a mutable bytearray and explicitly zeroizes
    it in memory when its context manager exits using ctypes.memset.
    """

    def __init__(self, value: str) -> None:
        self._data: bytearray | None = bytearray(value.encode("utf-8", "strict"))
        self._length: int = len(self._data)

    def get_value(self) -> str:
        if self._data is None:
            msg = "SecureString has already been zeroized or context exited."
            raise ValueError(msg)
        return self._data.decode("utf-8")

    def __enter__(self) -> "SecureString":
        return self

    def __exit__(self, exc_type: typing.Any, exc_val: typing.Any, exc_tb: typing.Any) -> None:
        self.zeroize()

    def zeroize(self) -> None:
        if self._data is not None:
            # Overwrite memory with zeros
            buf = (ctypes.c_char * self._length).from_buffer(self._data)
            ctypes.memset(ctypes.addressof(buf), 0, self._length)
            self._data = None
            self._length = 0
