import logging
import sqlite3
import tempfile
from pathlib import Path

from domain_models.manifest import Chunk, SummaryNode

logger = logging.getLogger(__name__)


class DiskChunkStore:
    """
    A temporary disk-based store for Chunks and SummaryNodes to avoid O(N) RAM usage.
    Uses SQLite with JSON serialization for security and interoperability.
    """

    def __init__(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "store.db"
        self._conn = sqlite3.connect(str(self.db_path))
        self._setup_db()

    def _setup_db(self) -> None:
        cursor = self._conn.cursor()
        # Enable WAL mode for performance
        cursor.execute("PRAGMA journal_mode=WAL;")
        # Store serialized objects as TEXT (JSON)
        cursor.execute("""
            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                type TEXT,
                data TEXT
            )
        """)
        self._conn.commit()

    def add_chunk(self, chunk: Chunk) -> None:
        """Store a chunk. ID is its index converted to str."""
        self.add_chunks([chunk])

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Store multiple chunks in a batch."""
        if not chunks:
            return
        params = [
            (str(c.index), "chunk", c.model_dump_json()) for c in chunks
        ]
        with self._conn:
            self._conn.executemany(
                "INSERT OR REPLACE INTO nodes (id, type, data) VALUES (?, ?, ?)",
                params,
            )

    def add_summary(self, node: SummaryNode) -> None:
        """Store a summary node."""
        self.add_summaries([node])

    def add_summaries(self, nodes: list[SummaryNode]) -> None:
        """Store multiple summary nodes in a batch."""
        if not nodes:
            return
        params = [
            (n.id, "summary", n.model_dump_json()) for n in nodes
        ]
        with self._conn:
            self._conn.executemany(
                "INSERT OR REPLACE INTO nodes (id, type, data) VALUES (?, ?, ?)",
                params,
            )

    def get_node(self, node_id: int | str) -> Chunk | SummaryNode | None:
        """Retrieve a node by ID."""
        cursor = self._conn.execute("SELECT type, data FROM nodes WHERE id = ?", (str(node_id),))
        row = cursor.fetchone()
        if not row:
            return None

        node_type, data = row

        try:
            if node_type == "chunk":
                return Chunk.model_validate_json(data)
            if node_type == "summary":
                return SummaryNode.model_validate_json(data)
        except Exception:
            logger.exception(f"Failed to deserialize node {node_id}")
            return None

        return None

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __enter__(self) -> "DiskChunkStore":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
