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
    Reverse-DIKW Level definitions.
    """

    WISDOM = "wisdom"
    KNOWLEDGE = "knowledge"
    INFORMATION = "information"
    DATA = "data"

from enum import Enum

class CanvasNodeType(str, Enum):
    TEXT = "text"
    FILE = "file"
    GROUP = "group"
