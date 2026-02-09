from typing import Any, TypeAlias

# NodeID can be an integer (Chunk index) or a string (SummaryNode UUID).
NodeID: TypeAlias = int | str

# Metadata is a flexible dictionary used to store arbitrary context.
Metadata: TypeAlias = dict[str, Any]
