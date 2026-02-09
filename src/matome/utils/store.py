import logging
import shutil
import tempfile
from pathlib import Path

from sqlalchemy import Column, MetaData, String, Table, Text, create_engine, text

from domain_models.manifest import Chunk, SummaryNode

logger = logging.getLogger(__name__)


class DiskChunkStore:
    """
    A temporary disk-based store for Chunks and SummaryNodes to avoid O(N) RAM usage.
    Uses SQLAlchemy + SQLite for robustness and connection pooling.
    """

    def __init__(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "store.db"
        # Use standard SQLite URL
        db_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(db_url)
        self._setup_db()

    def _setup_db(self) -> None:
        """Initialize the database schema."""
        with self.engine.begin() as conn:
            # Enable WAL mode for performance
            conn.execute(text("PRAGMA journal_mode=WAL;"))

        # Define schema using SQLAlchemy Core
        metadata = MetaData()
        self.nodes_table = Table(
            "nodes",
            metadata,
            Column("id", String, primary_key=True),
            Column("type", String),
            Column("data", Text),
        )
        metadata.create_all(self.engine)

    def add_chunk(self, chunk: Chunk) -> None:
        """Store a chunk. ID is its index converted to str."""
        self.add_chunks([chunk])

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Store multiple chunks in a batch."""
        if not chunks:
            return

        # Prepare parameters for bulk insert
        params = [
            {"id": str(c.index), "type": "chunk", "data": c.model_dump_json()}
            for c in chunks
        ]

        stmt = text("INSERT OR REPLACE INTO nodes (id, type, data) VALUES (:id, :type, :data)")

        # Use engine.begin() for transaction management (auto-commit)
        with self.engine.begin() as conn:
            conn.execute(stmt, params)

    def add_summary(self, node: SummaryNode) -> None:
        """Store a summary node."""
        self.add_summaries([node])

    def add_summaries(self, nodes: list[SummaryNode]) -> None:
        """Store multiple summary nodes in a batch."""
        if not nodes:
            return

        params = [
            {"id": n.id, "type": "summary", "data": n.model_dump_json()}
            for n in nodes
        ]

        stmt = text("INSERT OR REPLACE INTO nodes (id, type, data) VALUES (:id, :type, :data)")

        with self.engine.begin() as conn:
            conn.execute(stmt, params)

    def update_node_embedding(self, node_id: int | str, embedding: list[float]) -> None:
        """
        Update the embedding of an existing node.
        Fetches the node, updates the embedding, and saves it back.
        """
        node = self.get_node(node_id)
        if not node:
            logger.warning(f"Attempted to update embedding for non-existent node {node_id}")
            return

        # Update embedding field
        # Use model_copy to ensure validation if needed, or direct assignment if mutable?
        # Pydantic models are mutable by default unless frozen=True.
        # Check domain_models/manifest.py: Chunk config extra='forbid', validate_assignment=True.
        # But allow mutation? No, config doesn't say frozen=True.
        # SummaryNode config extra='forbid'.
        # Let's try direct assignment.
        try:
            node.embedding = embedding
        except Exception:
            # If frozen, use model_copy with update
            node = node.model_copy(update={"embedding": embedding})

        # Save back based on type
        if isinstance(node, Chunk):
            self.add_chunk(node)
        elif isinstance(node, SummaryNode):
            self.add_summary(node)

    def get_node(self, node_id: int | str) -> Chunk | SummaryNode | None:
        """Retrieve a node by ID."""
        stmt = text("SELECT type, data FROM nodes WHERE id = :id")

        # Use connect() for read-only if possible, but standard execute is fine
        with self.engine.connect() as conn:
            result = conn.execute(stmt, {"id": str(node_id)})
            row = result.fetchone()

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
        """
        Explicit commit.
        In this implementation using SQLAlchemy with auto-commit blocks,
        this is mostly a placeholder or synchronization point.
        """

    def close(self) -> None:
        """Close the engine and cleanup temp files."""
        self.engine.dispose()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __enter__(self) -> "DiskChunkStore":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
