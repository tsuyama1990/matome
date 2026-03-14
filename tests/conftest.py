import pytest


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Suppress exit code 5 (no tests found)."""
    if exitstatus == 5:
        session.exitstatus = 0
