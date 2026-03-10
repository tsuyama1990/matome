import time

from src.utils.rate_limit import RateLimiter, rate_limit


def test_rate_limiter_zero_limit() -> None:
    limiter = RateLimiter(0.0)
    start = time.time()
    limiter.acquire()
    limiter.acquire()
    end = time.time()
    assert (end - start) < 0.1


def test_rate_limiter_positive_limit() -> None:
    limit = 0.1
    limiter = RateLimiter(limit)
    start = time.time()
    limiter.acquire()
    limiter.acquire()
    end = time.time()
    assert (end - start) >= limit


def test_rate_limit_decorator() -> None:
    @rate_limit(0.1)
    def fast_func() -> str:
        return "done"

    start = time.time()
    fast_func()
    fast_func()
    end = time.time()

    assert (end - start) >= 0.1
    assert fast_func() == "done"
