import contextlib
import json
import logging
import shutil
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path

from domain_models.constants import (
    COL_CONTENT,
    COL_EMBEDDING,
    COL_ID,
    COL_TYPE,
    TABLE_NODES,
)
from domain_models.manifest import Chunk, SummaryNode
from matome.utils.compat import batched

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def get_db_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
    """
    Context manager for SQLite connections.
    Ensures proper closing and handles timeouts for concurrency.
    """
    # check_same_thread=False is safe because we create a new connection per thread/context
    # and we don't share cursor objects across threads.
    conn = sqlite3.connect(db_path, timeout=20.0, check_same_thread=False)

    # Enable WAL mode for better concurrency (readers don't block writers)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class DiskChunkStore:
    """
    A temporary disk-based store for Chunks and SummaryNodes to avoid O(N) RAM usage.
    Uses raw SQLite3 with context managers for thread-safe concurrency.

    Schema:
        id: String PK
        type: String ('chunk' or 'summary')
        content: Text (JSON representation of the node, potentially excluding embedding)
        embedding: Text (JSON representation of the embedding list, allowing independent updates)
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialize the store.

        Args:
            db_path: Optional path to the database file. If None, a secure temporary file is created.
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

        self._setup_db()

    def _setup_db(self) -> None:
        """Initialize the database schema."""
        with get_db_connection(self.db_path) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NODES} (
                    {COL_ID} TEXT PRIMARY KEY,
                    {COL_TYPE} TEXT,
                    {COL_CONTENT} TEXT,
                    {COL_EMBEDDING} TEXT
                )
            """)

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

    def _add_nodes(self, nodes: Iterable[Chunk | SummaryNode], node_type: str) -> None:
        """
        Helper to batch insert nodes.
        Streaming safe: processes input iterable in batches without full materialization.
        """
        BATCH_SIZE = 1000

        sql = f"""
            INSERT OR REPLACE INTO {TABLE_NODES} ({COL_ID}, {COL_TYPE}, {COL_CONTENT}, {COL_EMBEDDING})
            VALUES (?, ?, ?, ?)
        """  # noqa: S608

        # Iterate over the input iterable using batched() to handle chunks efficiently
        for node_batch in batched(nodes, BATCH_SIZE):
            buffer = []
            for node in node_batch:
                # Pydantic v2 model_dump_json supports `exclude={'embedding'}`.
                content_json = node.model_dump_json(exclude={"embedding"})

                # Embedding JSON
                embedding_json = json.dumps(node.embedding) if node.embedding is not None else None

                node_id = str(node.index) if isinstance(node, Chunk) else node.id

                buffer.append((node_id, node_type, content_json, embedding_json))

            # Flush batch
            with get_db_connection(self.db_path) as conn:
                conn.executemany(sql, buffer)

    def update_node_embedding(self, node_id: int | str, embedding: list[float]) -> None:
        """
        Update the embedding of an existing node efficiently.
        Executes a direct UPDATE without fetching the node first.
        """
        if embedding is None:
            return

        embedding_json = json.dumps(embedding)

        sql = f"UPDATE {TABLE_NODES} SET {COL_EMBEDDING} = ? WHERE {COL_ID} = ?"  # noqa: S608

        with get_db_connection(self.db_path) as conn:
            conn.execute(sql, (embedding_json, str(node_id)))

    def update_embeddings(self, updates: Iterable[tuple[int | str, list[float]]]) -> None:
        """
        Batch update embeddings.
        Args:
            updates: Iterable of (node_id, embedding_vector) tuples.
        """
        BATCH_SIZE = 1000
        sql = f"UPDATE {TABLE_NODES} SET {COL_EMBEDDING} = ? WHERE {COL_ID} = ?"  # noqa: S608

        for batch in batched(updates, BATCH_SIZE):
            buffer = []
            for node_id, embedding in batch:
                if embedding is None:
                    continue
                embedding_json = json.dumps(embedding)
                buffer.append((embedding_json, str(node_id)))

            if not buffer:
                continue

            with get_db_connection(self.db_path) as conn:
                conn.executemany(sql, buffer)

    def get_node(self, node_id: int | str) -> Chunk | SummaryNode | None:
        """Retrieve a node by ID."""

        sql = f"SELECT {COL_TYPE}, {COL_CONTENT}, {COL_EMBEDDING} FROM {TABLE_NODES} WHERE {COL_ID} = ?"  # noqa: S608

        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute(sql, (str(node_id),))
            row = cursor.fetchone()

            if not row:
                return None

            node_type, content_json, embedding_json = row

            try:
                # Deserialize embedding first
                embedding = json.loads(embedding_json) if embedding_json else None

                # Parse JSON then validate to ensure strict type compliance
                data = json.loads(content_json)
                if embedding is not None:
                    data["embedding"] = embedding

                if node_type == "chunk":
                    return Chunk.model_validate(data)

                if node_type == "summary":
                    return SummaryNode.model_validate(data)

            except Exception:
                logger.exception(f"Failed to deserialize node {node_id}")
                return None

        return None

    def get_nodes_by_level(self, level: str) -> list[SummaryNode]:
        """
        Retrieve all SummaryNodes matching a specific DIKW level.
        Note: This performs a full scan of summary nodes and filters in Python.
        """
        sql = f"SELECT {COL_CONTENT}, {COL_EMBEDDING} FROM {TABLE_NODES} WHERE {COL_TYPE} = ?"  # noqa: S608

        nodes: list[SummaryNode] = []

        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute(sql, ("summary",))
            rows = cursor.fetchall()

        for content_json, embedding_json in rows:
            try:
                data = json.loads(content_json)
                if embedding_json:
                    data["embedding"] = json.loads(embedding_json)

                node = SummaryNode.model_validate(data)

                # Check DIKW level
                if node.metadata.dikw_level == level:
                    nodes.append(node)

            except Exception:
                logger.exception("Failed to deserialize summary node during level filtering")

        return nodes

    def get_nodes(self, node_ids: list[int | str]) -> dict[int | str, Chunk | SummaryNode | None]:
        """
        Retrieve multiple nodes by ID in a single query.
        Returns a dictionary mapping ID to Node object (or None).
        """
        if not node_ids:
            return {}

        # Determine strict mapping for return keys
        # We want to return exactly the same type/value of key as requested
        # But DB returns string IDs.

        # Helper to normalize ID for DB query
        str_ids = [str(nid) for nid in node_ids]

        # We can't use placeholders for IN clause with list directly in sqlite3 standard execute,
        # need to construct string with correct number of ?
        # But for huge lists, this hits SQL limits.
        # So we should batch the retrieval too.

        BATCH_SIZE = 900  # SQLite limit is typically 999 vars
        results: dict[int | str, Chunk | SummaryNode | None] = {}

        # Pre-fill with None to ensure all keys exist
        for nid in node_ids:
            results[nid] = None

        for batch_ids in batched(str_ids, BATCH_SIZE):
            # We need to map back from str_id to original ID type if needed.
            batch_ids_list = list(batch_ids)
            placeholders = ",".join("?" for _ in batch_ids_list)
            sql = f"SELECT {COL_ID}, {COL_TYPE}, {COL_CONTENT}, {COL_EMBEDDING} FROM {TABLE_NODES} WHERE {COL_ID} IN ({placeholders})"  # noqa: S608

            rows = []
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute(sql, batch_ids_list)
                rows = cursor.fetchall()

            for row in rows:
                self._deserialize_and_store_node(row, results)

        return results

    def _deserialize_and_store_node(
        self,
        row: tuple[str, str, str, str | None],
        results: dict[int | str, Chunk | SummaryNode | None],
    ) -> None:
        """Deserialize a node row and store in results if requested."""
        node_id_str, node_type, content_json, embedding_json = row
        try:
            embedding = json.loads(embedding_json) if embedding_json else None
            data = json.loads(content_json)
            if embedding is not None:
                data["embedding"] = embedding

            node: Chunk | SummaryNode
            if node_type == "chunk":
                node = Chunk.model_validate(data)
                # Map back to original key(s)
                if node.index in results:
                    results[node.index] = node
                if str(node.index) in results:
                    results[str(node.index)] = node

            elif node_type == "summary":
                node = SummaryNode.model_validate(data)
                if node.id in results:
                    results[node.id] = node

        except Exception:
            logger.exception(f"Failed to deserialize node {node_id_str}")

    def commit(self) -> None:
        """Explicit commit (placeholder as we use auto-commit blocks)."""

    def close(self) -> None:
        """Close the engine and cleanup temp files."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __enter__(self) -> "DiskChunkStore":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
