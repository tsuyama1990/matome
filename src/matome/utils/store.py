import contextlib
import json
import logging
import re
import shutil
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final

from sqlalchemy import (
    Integer,
    cast,
    create_engine,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from domain_models.constants import MAX_DB_CONTENT_LENGTH
from domain_models.manifest import Chunk, SummaryNode
from matome.exceptions import StoreError
from matome.utils.compat import batched
from matome.utils.serialization import deserialize_node
from matome.utils.store_schema import metadata, nodes_table

logger = logging.getLogger(__name__)

# Configuration Constants
DEFAULT_WRITE_BATCH_SIZE: Final[int] = 1000
DEFAULT_READ_BATCH_SIZE: Final[int] = 500
# Allow alphanumeric, underscore, hyphen only to prevent injection
VALID_NODE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_\-]+$")


class DiskChunkStore:
    """
    A temporary disk-based store for Chunks and SummaryNodes to avoid O(N) RAM usage.
    Uses SQLAlchemy + SQLite for robustness and connection pooling.

    Schema:
        id: String PK
        type: String ('chunk' or 'summary')
        content: Text (JSON representation of the node, potentially excluding embedding)
        embedding: Text (JSON representation of the embedding list, allowing independent updates)
    """

    def __init__(
        self,
        db_path: Path | None = None,
        write_batch_size: int = DEFAULT_WRITE_BATCH_SIZE,
        read_batch_size: int = DEFAULT_READ_BATCH_SIZE,
    ) -> None:
        """
        Initialize the store.

        Args:
            db_path: Optional path to the database file. If None, a secure temporary file is created.
            write_batch_size: Batch size for writing operations.
            read_batch_size: Batch size for reading operations.
        """
        if db_path:
            self.temp_dir = None
            # Security: Resolve to absolute path to handle relative paths and '..' safely
            try:
                self.db_path = db_path.resolve()
            except OSError:
                # Fallback if file doesn't exist yet but parent might
                self.db_path = db_path.absolute()
        else:
            self.temp_dir = tempfile.mkdtemp()
            self.db_path = Path(self.temp_dir) / "store.db"

        self.write_batch_size = write_batch_size
        self.read_batch_size = read_batch_size

        # Use standard SQLite URL
        db_url = f"sqlite:///{self.db_path}"

        # Configure connection pooling for performance
        # SQLite handles concurrency poorly with multiple writers, but we use WAL mode.
        try:
            self.engine: Engine = create_engine(
                db_url, pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=1800
            )
        except Exception as e:
            msg = f"Failed to create database engine: {e}"
            raise StoreError(msg) from e

        self._setup_db()

    def _setup_db(self) -> None:
        """Initialize the database schema."""
        try:
            with self.engine.begin() as conn:
                # Enable WAL mode for performance
                conn.execute(text("PRAGMA journal_mode=WAL;"))
                # Synchronous NORMAL is faster and safe enough for WAL
                conn.execute(text("PRAGMA synchronous=NORMAL;"))
        except SQLAlchemyError as e:
            msg = f"Failed to configure database PRAGMAs: {e}"
            raise StoreError(msg) from e

        self.nodes_table = nodes_table
        try:
            metadata.create_all(self.engine)
        except SQLAlchemyError as e:
            msg = f"Failed to create database schema: {e}"
            raise StoreError(msg) from e

    def _validate_node_id(self, node_id: str) -> str:
        """Validate node ID format to prevent injection/corruption."""
        if not VALID_NODE_ID_PATTERN.match(node_id):
            msg = f"Invalid node ID format: {node_id}"
            raise ValueError(msg)
        return node_id

    def add_chunk(self, chunk: Chunk) -> None:
        """Store a chunk. ID is its index converted to str."""
        self.add_chunks([chunk])

    def add_chunks(self, chunks: Iterable[Chunk]) -> None:
        """Store multiple chunks in a batch."""
        self._add_nodes(chunks, "chunk")

    def add_summary(self, node: SummaryNode) -> None:
        """Store a summary node."""
        self.add_summaries([node])

    def add_summaries(self, nodes: Iterable[SummaryNode]) -> None:
        """Store multiple summary nodes in a batch."""
        self._add_nodes(nodes, "summary")

    def _validate_content_length(self, content: str) -> None:
        """Validate content length."""
        if len(content) > MAX_DB_CONTENT_LENGTH:
            msg = f"Node content length ({len(content)}) exceeds limit ({MAX_DB_CONTENT_LENGTH})."
            raise ValueError(msg)

    def _add_nodes(self, nodes: Iterable[Chunk | SummaryNode], node_type: str) -> None:
        """
        Helper to batch insert nodes.
        Streaming safe: processes input iterable in batches without full materialization.
        """
        # Use Core Insert with REPLACE logic for SQLite
        stmt = insert(self.nodes_table).prefix_with("OR REPLACE")

        try:
            # Iterate over the input iterable using batched() to handle chunks efficiently
            for node_batch in batched(nodes, self.write_batch_size):
                buffer: list[dict[str, Any]] = []

                for node in node_batch:
                    content_json = node.model_dump_json(exclude={"embedding"})
                    self._validate_content_length(content_json)

                    embedding_json = json.dumps(node.embedding) if node.embedding is not None else None
                    node_id = str(node.index) if isinstance(node, Chunk) else str(node.id)

                    # Validate ID
                    self._validate_node_id(node_id)

                    buffer.append(
                        {
                            "id": node_id,
                            "type": node_type,
                            "content": content_json,
                            "embedding": embedding_json,
                        }
                    )

                # Flush batch with transaction
                with self.engine.begin() as conn:
                    conn.execute(stmt, buffer)
        except SQLAlchemyError as e:
            msg = f"Failed to add nodes to store: {e}"
            raise StoreError(msg) from e
        except ValueError:
            # Validation errors pass through
            raise
        except Exception as e:
            # Catch-all for unexpected errors (e.g., batched failure)
            msg = f"Unexpected error adding nodes: {e}"
            raise StoreError(msg) from e

    def get_nodes(self, node_ids: Iterable[str | int]) -> Iterator[Chunk | SummaryNode]:
        """
        Retrieve multiple nodes by ID.
        Iterates over input IDs in batches, queries DB, and yields results via streaming.
        Accepts str or int IDs and normalizes them.

        Note: Does NOT guarantee output order matches input order.
        Yields only found nodes. Missing nodes are skipped.
        """
        # Connect once outside the loop to optimize connection usage
        try:
            with self.engine.connect() as conn:
                # Consume the iterable in batches to avoid loading all IDs into memory if it's a generator
                for batch_raw_ids in batched(node_ids, self.read_batch_size):
                    # Normalize and validate IDs in batch efficiently
                    batch_ids: list[str] = []
                    for raw_id in batch_raw_ids:
                        normalized_id = str(raw_id)
                        if not VALID_NODE_ID_PATTERN.match(normalized_id):
                            # We might log this but skipping is safer to avoid injection
                            logger.warning(f"Skipping invalid node ID: {normalized_id}")
                            continue
                        batch_ids.append(normalized_id)

                    if not batch_ids:
                        continue

                    stmt = select(
                        self.nodes_table.c.id,
                        self.nodes_table.c.type,
                        self.nodes_table.c.content,
                        self.nodes_table.c.embedding,
                    ).where(self.nodes_table.c.id.in_(batch_ids))

                    # stream_results=True minimizes memory usage for the result set
                    result = conn.execution_options(stream_results=True).execute(stmt)

                    for row in result:
                        try:
                            yield deserialize_node(
                                row.id, row.type, row.content, row.embedding
                            )
                        except Exception:
                            logger.exception(f"Error deserializing node {row.id}")
                            continue
        except SQLAlchemyError as e:
            msg = f"Failed to retrieve nodes: {e}"
            raise StoreError(msg) from e
        except Exception as e:
            msg = f"Unexpected error retrieving nodes: {e}"
            raise StoreError(msg) from e

    def update_node_embedding(self, node_id: int | str, embedding: list[float]) -> None:
        """
        Update the embedding of an existing node efficiently.
        Executes a direct UPDATE without fetching the node first.
        """
        if embedding is None:
            return

        node_id_str = str(node_id)
        self._validate_node_id(node_id_str)
        embedding_json = json.dumps(embedding)

        stmt = (
            update(self.nodes_table)
            .where(self.nodes_table.c.id == node_id_str)
            .values(embedding=embedding_json)
        )

        try:
            with self.engine.begin() as conn:
                result = conn.execute(stmt)
                if result.rowcount == 0:
                    msg = f"Node {node_id} not found."
                    raise StoreError(msg)
        except SQLAlchemyError as e:
            msg = f"Failed to update embedding for node {node_id}: {e}"
            raise StoreError(msg) from e

    def update_node(self, node: SummaryNode) -> None:
        """
        Update an existing summary node.
        """
        content_json = node.model_dump_json(exclude={"embedding"})
        embedding_json = json.dumps(node.embedding) if node.embedding is not None else None

        self._validate_node_id(str(node.id))

        stmt = (
            update(self.nodes_table)
            .where(self.nodes_table.c.id == node.id)
            .values(content=content_json, embedding=embedding_json)
        )

        try:
            with self.engine.begin() as conn:
                result = conn.execute(stmt)
                if result.rowcount == 0:
                    msg = f"Node {node.id} not found."
                    raise StoreError(msg)
        except SQLAlchemyError as e:
            msg = f"Failed to update node {node.id}: {e}"
            raise StoreError(msg) from e

    def get_node(self, node_id: int | str) -> Chunk | SummaryNode | None:
        """Retrieve a node by ID."""
        node_id_str = str(node_id)
        self._validate_node_id(node_id_str)

        stmt = select(
            self.nodes_table.c.type, self.nodes_table.c.content, self.nodes_table.c.embedding
        ).where(self.nodes_table.c.id == node_id_str)

        try:
            with self.engine.connect() as conn:
                result = conn.execute(stmt)
                row = result.fetchone()

                if not row:
                    return None

                node_type, content_json, embedding_json = row
                return deserialize_node(node_id_str, node_type, content_json, embedding_json)
        except SQLAlchemyError as e:
            msg = f"Failed to retrieve node {node_id}: {e}"
            raise StoreError(msg) from e
        except ValueError:
            raise
        except Exception as e:
            msg = f"Unexpected error retrieving node {node_id}: {e}"
            raise StoreError(msg) from e

    def get_node_ids_by_level(self, level: int) -> Iterator[str]:
        """
        Stream node IDs for a specific hierarchical level.
        Uses database index for efficiency.
        """
        # Optimized: If level is 0, we can filter by type='chunk' which is faster.
        if level == 0:
            stmt = (
                select(self.nodes_table.c.id)
                .where(self.nodes_table.c.type == "chunk")
                .order_by(cast(self.nodes_table.c.id, Integer))
            )
        else:
            # Uses the index on json_extract(content, '$.level')
            # SQLAlchemy handles parameter binding of `level` safely when used in comparison expression.
            # "$.level" is a constant path string, not user input.
            stmt = (
                select(self.nodes_table.c.id)
                .where(
                    self.nodes_table.c.type == "summary",
                    func.json_extract(self.nodes_table.c.content, "$.level") == level,
                )
                .order_by(self.nodes_table.c.id)
            )

        try:
            with self.engine.connect() as conn:
                # Stream results to avoid loading all IDs into memory at once
                result = conn.execution_options(stream_results=True).execute(stmt)
                for row in result:
                    yield row[0]
        except SQLAlchemyError as e:
            msg = f"Failed to stream node IDs for level {level}: {e}"
            raise StoreError(msg) from e

    def get_node_count(self, level: int) -> int:
        """
        Get the number of nodes at a specific level.
        Efficient count query.
        """
        if level == 0:
            stmt = select(func.count()).where(self.nodes_table.c.type == "chunk")
        else:
            stmt = select(func.count()).where(
                self.nodes_table.c.type == "summary",
                func.json_extract(self.nodes_table.c.content, "$.level") == level,
            )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(stmt)
                return result.scalar() or 0
        except SQLAlchemyError as e:
            msg = f"Failed to count nodes at level {level}: {e}"
            raise StoreError(msg) from e

    def get_max_level(self) -> int:
        """
        Get the maximum level present in the store.
        Returns 0 if no summary nodes exist.
        """
        stmt = select(
            func.max(
                cast(func.json_extract(self.nodes_table.c.content, "$.level"), Integer)
            )
        ).where(self.nodes_table.c.type == "summary")

        try:
            with self.engine.connect() as conn:
                result = conn.execute(stmt)
                return result.scalar() or 0
        except SQLAlchemyError as e:
            msg = f"Failed to get max level: {e}"
            raise StoreError(msg) from e

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        """
        Context manager for an explicit transaction.
        Note: Engine.begin() handles transaction lifecycle.
        """
        try:
            with self.engine.begin() as conn:
                yield conn
        except SQLAlchemyError as e:
            msg = f"Transaction failed: {e}"
            raise StoreError(msg) from e

    def commit(self) -> None:
        """Explicit commit (placeholder as we use auto-commit blocks)."""

    def close(self) -> None:
        """Close the engine and cleanup temp files."""
        with contextlib.suppress(Exception):
            self.engine.dispose()
        if self.temp_dir:
            with contextlib.suppress(Exception):
                shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __enter__(self) -> "DiskChunkStore":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
