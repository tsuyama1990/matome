from enum import StrEnum
from typing import Any, TypeAlias

# NodeID can be an integer (Chunk index) or a string (SummaryNode UUID).
# - int: Refers to a leaf Chunk node (0-indexed).
# - str: Refers to a SummaryNode (UUID string).
NodeID: TypeAlias = int | str

# Metadata is a flexible dictionary used to store arbitrary context.
# e.g., {"filename": "doc.txt", "author": "User", "timestamp": "2023-01-01"}
Metadata: TypeAlias = dict[str, Any]


class DIKWLevel(StrEnum):
    """
    DIKW (Data, Information, Knowledge, Wisdom) Hierarchy Levels.
    """

    WISDOM = "wisdom"  # L1
    KNOWLEDGE = "knowledge"  # L2
    INFORMATION = "information"  # L3
    DATA = "data"  # L4 (Leaf chunks)
