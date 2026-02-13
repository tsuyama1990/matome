"""
DEPRECATED: This module is deprecated and will be removed in future cycles.
Please import from 'matome.agents.strategies' instead.
"""

import warnings

from matome.agents.strategies import (
    BaseSummaryStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)

# DefaultStrategy was an alias for BaseSummaryStrategy in the old file,
# or simply not present in the new file. We map it to BaseSummaryStrategy for compatibility.
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
    "WisdomStrategy",
]
