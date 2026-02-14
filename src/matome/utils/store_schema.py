from typing import Final

from sqlalchemy import (
    Column,
    Index,
    MetaData,
    String,
    Table,
    Text,
    func,
    text,
)

# Constants for DB Schema
TABLE_NODES: Final[str] = "nodes"
COL_ID: Final[str] = "id"
COL_TYPE: Final[str] = "type"
COL_CONTENT: Final[str] = "content"  # Stores JSON of the node (excluding embedding)
COL_EMBEDDING: Final[str] = "embedding"  # Stores JSON of the embedding list

# Define schema using SQLAlchemy Core
metadata = MetaData()
nodes_table = Table(
    TABLE_NODES,
    metadata,
    Column(COL_ID, String, primary_key=True),
    Column(COL_TYPE, String),
    Column(COL_CONTENT, Text),  # Main node data
    Column(COL_EMBEDDING, Text),  # Embedding separated for efficient updates
    # Index on extracted JSON level field for performance
    Index(
        "idx_nodes_level",
        func.json_extract(text(COL_CONTENT), "$.level"),
    ),
    # Composite index for optimization of get_node_ids_by_level
    Index(
        "idx_nodes_type_level",
        COL_TYPE,
        func.json_extract(text(COL_CONTENT), "$.level"),
    ),
)
