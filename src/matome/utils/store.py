import logging
import pickle
import sqlite3
import tempfile
from pathlib import Path

from domain_models.manifest import Chunk, SummaryNode

logger = logging.getLogger(__name__)

class DiskChunkStore:
    """
    A temporary disk-based store for Chunks and SummaryNodes to avoid O(N) RAM usage.
    Uses SQLite with binary serialization (pickle) for efficiency.
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
        # Store serialized objects as BLOB
        cursor.execute("""
            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                type TEXT,
                data BLOB
            )
        """)
        self._conn.commit()

    def add_chunk(self, chunk: Chunk) -> None:
        """Store a chunk. ID is its index converted to str."""
        data = pickle.dumps(chunk, protocol=pickle.HIGHEST_PROTOCOL)
        self._conn.execute(
            "INSERT OR REPLACE INTO nodes (id, type, data) VALUES (?, ?, ?)",
            (str(chunk.index), "chunk", data)
        )

    def add_summary(self, node: SummaryNode) -> None:
        """Store a summary node."""
        data = pickle.dumps(node, protocol=pickle.HIGHEST_PROTOCOL)
        self._conn.execute(
            "INSERT OR REPLACE INTO nodes (id, type, data) VALUES (?, ?, ?)",
            (node.id, "summary", data)
        )

    def get_node(self, node_id: int | str) -> Chunk | SummaryNode | None:
        """Retrieve a node by ID."""
        cursor = self._conn.execute(
            "SELECT type, data FROM nodes WHERE id = ?",
            (str(node_id),)
        )
        row = cursor.fetchone()
        if not row:
            return None

        node_type, data = row
        obj = pickle.loads(data)  # noqa: S301

        if node_type == "chunk":
            if not isinstance(obj, Chunk):
                 logger.error(f"Retrieved object for {node_id} is not a Chunk.")
                 return None
            return obj
        if node_type == "summary":
            if not isinstance(obj, SummaryNode):
                 logger.error(f"Retrieved object for {node_id} is not a SummaryNode.")
                 return None
            return obj
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
