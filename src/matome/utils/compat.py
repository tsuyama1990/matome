"""
Compatibility utility for older Python versions.
Provides backports for features introduced in newer Python versions.
"""

import itertools
from collections.abc import Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")


def batched(iterable: Iterable[T], n: int) -> Iterator[tuple[T, ...]]:
    """
    Batch data into tuples of length n. The last batch may be shorter.

    This is a backport of itertools.batched (Python 3.12+).

    Args:
        iterable: The input iterable.
        n: The size of each batch (must be >= 1).

    Yields:
        Tuples of elements from the iterable.

    Raises:
        ValueError: If n < 1.
    """
    if n < 1:
        msg = "n must be at least one"
        raise ValueError(msg)

    # Check if itertools has batched (Python 3.12+)
    if hasattr(itertools, "batched"):
        yield from itertools.batched(iterable, n)
        return

    # Polyfill for Python < 3.12
    it = iter(iterable)
    while True:
        batch = tuple(itertools.islice(it, n))
        if not batch:
            break
        yield batch
