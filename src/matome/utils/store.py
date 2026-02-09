import json
import logging
import shutil
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sqlalchemy import Column, MetaData, String, Table, Text, create_engine, text

from domain_models.manifest import Chunk, SummaryNode

logger = logging.getLogger(__name__)

# Constants for DB Schema
TABLE_NODES = "nodes"
COL_ID = "id"
COL_TYPE = "type"
COL_CONTENT = "content"  # Stores JSON of the node (excluding embedding)
COL_EMBEDDING = "embedding"  # Stores JSON of the embedding list


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

    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialize the store.

        Args:
            db_path: Optional path to the database file. If None, a secure temporary file is created.
        """
        if db_path:
            self.temp_dir = None
            self.db_path = db_path
        else:
            self.temp_dir = tempfile.mkdtemp()
            self.db_path = Path(self.temp_dir) / "store.db"

        # Use standard SQLite URL
        # Security: db_path is constructed safely via tempfile or passed explicitly by trusted caller.
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
            TABLE_NODES,
            metadata,
            Column(COL_ID, String, primary_key=True),
            Column(COL_TYPE, String),
            Column(COL_CONTENT, Text),  # Main node data
            Column(COL_EMBEDDING, Text),  # Embedding separated for efficient updates
        )
        metadata.create_all(self.engine)

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
        """Helper to batch insert nodes."""
        # We need to process the iterable in batches to avoid O(N) memory usage
        # collecting parameters.
        BATCH_SIZE = 1000
        buffer: list[dict[str, Any]] = []

        # Construct query string (safe because using internal constants)
        query = (
            f"INSERT OR REPLACE INTO {TABLE_NODES} ({COL_ID}, {COL_TYPE}, {COL_CONTENT}, {COL_EMBEDDING}) "
            f"VALUES (:id, :type, :content, :embedding)"
        )
        stmt = text(query)  # noqa: S608

        with self.engine.begin() as conn:
            for node in nodes:
                # Prepare data
                # We strip embedding from content to save space/redundancy if desired,
                # but Pydantic's model_dump_json includes it.
                # To efficiently separate, we can dump, load, pop, dump? Too slow.
                # Or just duplicate? Duplication wastes space but is simpler.
                # BETTER: Use 'exclude' in model_dump_json if possible, or just accept duplication.
                # Pydantic v2 model_dump_json supports `exclude={'embedding'}`.

                content_json = node.model_dump_json(exclude={"embedding"})

                # Embedding JSON
                embedding_json = json.dumps(node.embedding) if node.embedding is not None else None

                node_id = str(node.index) if isinstance(node, Chunk) else node.id

                buffer.append(
                    {
                        "id": node_id,
                        "type": node_type,
                        "content": content_json,
                        "embedding": embedding_json,
                    }
                )

                if len(buffer) >= BATCH_SIZE:
                    conn.execute(stmt, buffer)
                    buffer.clear()

            if buffer:
                conn.execute(stmt, buffer)

    def update_node_embedding(self, node_id: int | str, embedding: list[float]) -> None:
        """
        Update the embedding of an existing node efficiently.
        Executes a direct UPDATE without fetching the node first.
        """
        if embedding is None:
            return

        stmt = text(f"UPDATE {TABLE_NODES} SET {COL_EMBEDDING} = :embedding WHERE {COL_ID} = :id")  # noqa: S608
        embedding_json = json.dumps(embedding)

        with self.engine.begin() as conn:
            conn.execute(stmt, {"embedding": embedding_json, "id": str(node_id)})

    def get_node(self, node_id: int | str) -> Chunk | SummaryNode | None:
        """Retrieve a node by ID."""
        # Construct query string (safe because using internal constants)
        query = f"SELECT {COL_TYPE}, {COL_CONTENT}, {COL_EMBEDDING} FROM {TABLE_NODES} WHERE {COL_ID} = :id"
        stmt = text(query)  # noqa: S608

        with self.engine.connect() as conn:
            result = conn.execute(stmt, {"id": str(node_id)})
            row = result.fetchone()

            if not row:
                return None

            node_type, content_json, embedding_json = row

            try:
                # Deserialize embedding first
                embedding = json.loads(embedding_json) if embedding_json else None

                if node_type == "chunk":
                    # Validate content (which lacks embedding field now)
                    # We need to re-inject embedding before validation if the model requires it?
                    # Chunk schema: embedding is optional (list[float] | None).
                    # So validation works without it.
                    obj = Chunk.model_validate_json(content_json)
                    # Inject embedding
                    if embedding is not None:
                        # Direct assignment works because we validate assignment or use default
                        obj.embedding = embedding
                    return obj

                if node_type == "summary":
                    obj = SummaryNode.model_validate_json(content_json)
                    if embedding is not None:
                        obj.embedding = embedding
                    return obj

            except Exception:
                logger.exception(f"Failed to deserialize node {node_id}")
                return None

        return None

    def commit(self) -> None:
        """Explicit commit (placeholder as we use auto-commit blocks)."""

    def close(self) -> None:
        """Close the engine and cleanup temp files."""
        self.engine.dispose()
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __enter__(self) -> "DiskChunkStore":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
