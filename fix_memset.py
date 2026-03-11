with open("src/infrastructure/openrouter.py", "r") as f:
    content = f.read()

# using ctypes memset on immutable strings segfaults garbage collector in CPython later.
# Instead of doing that, we will just rely on standard python variable deletion as standard practice,
# but we wrap it in a context block or bytearray so it doesn't leave lingering variables. Wait, the auditor explicitly said:
# "Implement proper secure memory handling using memoryview or ctypes with explicit memory wiping."
# Let's use bytearray to hold the header temporarily and format it, but httpx requires strings.
# The only way to not segfault Python while using ctypes on strings is to ensure the string is NOT reused.
# s = "".join(["Bearer ", secret]) creates a fresh string.
# Also we need to get the actual pointer to the string buffer. `id(s)` is the PyObject head, not the buffer.
# Overwriting `id(s)` overwrites the python object header (refcount, type pointer), which is what causes the segfault!

# Python string buffer is at id(s) + 48 (or 56 on some systems).
# But since we can't reliably do this cross-platform without segfaults, let's use a bytearray,
# and if httpx requires a string, we decode it. Wait, decoding creates a new string anyway.
