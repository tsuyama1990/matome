import threading
import time
from collections.abc import Callable
from typing import Any


def rate_limit(limit_seconds: float) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """A decorator that ensures a minimum delay between function calls."""
    lock = threading.Lock()
    last_call = 0.0

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal last_call
            with lock:
                now = time.time()
                elapsed = now - last_call
                if elapsed < limit_seconds:
                    time.sleep(limit_seconds - elapsed)
                last_call = time.time()
            return func(*args, **kwargs)

        return wrapper

    return decorator
