import threading
import time
from collections.abc import Callable
from typing import Any


class RateLimiter:
    def __init__(self, limit_seconds: float) -> None:
        self.limit_seconds = limit_seconds
        self.lock = threading.Lock()
        self.last_call = 0.0

    def acquire(self) -> None:
        if self.limit_seconds <= 0:
            return

        with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            if elapsed < self.limit_seconds:
                time.sleep(self.limit_seconds - elapsed)
            self.last_call = time.time()


def rate_limit(limit_seconds: float) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """A decorator that ensures a minimum delay between function calls."""
    limiter = RateLimiter(limit_seconds)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter.acquire()
            return func(*args, **kwargs)

        return wrapper

    return decorator
