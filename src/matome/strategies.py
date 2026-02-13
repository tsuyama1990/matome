"""
DEPRECATED: This module is deprecated and will be removed in future cycles.
Please import from 'matome.agents.strategies' instead.
"""

import warnings
from typing import Any

from matome.agents.strategies import (
    BaseSummaryStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    RefinementStrategy,
    WisdomStrategy,
)

# DefaultStrategy was an alias for BaseSummaryStrategy in the old file.
# We map it to BaseSummaryStrategy for compatibility.
DefaultStrategy = BaseSummaryStrategy

warnings.warn(
    "matome.strategies is deprecated. Use matome.agents.strategies instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "BaseSummaryStrategy",
    "DefaultStrategy",
    "InformationStrategy",
    "KnowledgeStrategy",
    "RefinementStrategy",
    "WisdomStrategy",
]


# This module should also export these so old code doesn't break
def __getattr__(name: str) -> Any:
    """Redirect attribute access to the new module."""
    if name == "BaseSummaryStrategy":
        return BaseSummaryStrategy
    if name == "InformationStrategy":
        return InformationStrategy
    if name == "KnowledgeStrategy":
        return KnowledgeStrategy
    if name == "WisdomStrategy":
        return WisdomStrategy
    if name == "RefinementStrategy":
        return RefinementStrategy
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)
