import re

with open("src/infrastructure/vector_store.py", "r") as f:
    content = f.read()

adapter_code = """
import asyncio
import uuid
from src.domain_models.document import SemanticChunk, ChunkMetadata
from src.interfaces.dependencies import VectorDBProtocol

class VectorDBAdapter(VectorDBProtocol):
    \"\"\"Adapts the generic VectorStoreProtocol to the domain-specific VectorDBProtocol.\"\"\"

    def __init__(self, vector_store: VectorStoreProtocol, collection_name: str = "matome") -> None:
        self._store = vector_store
        self._collection_name = collection_name

    async def upsert(self, chunks: list[SemanticChunk]) -> None:
        records = []
        for c in chunks:
            if not c.embedding:
                continue
            rec: dict[str, Any] = {
                "id": str(c.chunk_id),
                "embedding": c.embedding,
                "text": c.text,
            }
            if c.metadata:
                rec.update(c.metadata.model_dump())
            records.append(rec)

        await asyncio.to_thread(self._store.upsert, self._collection_name, records)

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter_metadata: dict[str, str] | None = None,
    ) -> list[SemanticChunk]:
        # Retrieve slightly more in case we need to filter
        limit = top_k * 2 if filter_metadata else top_k
        results = await asyncio.to_thread(self._store.search, self._collection_name, query_embedding, limit)

        chunks = []
        for r in results:
            metadata_dict = r.copy()
            chunk_id_str = metadata_dict.pop("id")
            metadata_dict.pop("score", None)
            metadata_dict.pop("embedding", None)
            text = metadata_dict.pop("text", "")

            # Client metadata is nested inside "metadata" or flat depending on store
            if "metadata" in metadata_dict and isinstance(metadata_dict["metadata"], dict):
                meta_source = metadata_dict["metadata"]
            else:
                meta_source = metadata_dict

            # Apply exact match filtering if requested
            if filter_metadata:
                match = True
                for k, v in filter_metadata.items():
                    if meta_source.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            # Construct safe ChunkMetadata mapping
            safe_meta = {}
            for k, v in meta_source.items():
                if k in ("source_file", "time_axis", "summary", "keywords", "author"):
                    safe_meta[k] = v

            meta = ChunkMetadata(**safe_meta) if safe_meta else None

            chunks.append(
                SemanticChunk(
                    chunk_id=uuid.UUID(chunk_id_str),
                    text=text,
                    embedding=r.get("embedding"),
                    metadata=meta
                )
            )

            if len(chunks) == top_k:
                break

        return chunks
"""

if "class VectorDBAdapter" not in content:
    with open("src/infrastructure/vector_store.py", "a") as f:
        f.write("\n" + adapter_code + "\n")

with open("src/interfaces/dependencies.py", "r") as f:
    dep_content = f.read()

# Replace the fallback mapping
old_vector_db_factory = """    def vector_db_factory() -> VectorDBProtocol:
        from src.infrastructure.test_services import FallbackVectorDB

        return FallbackVectorDB()

    container.register(VectorDBProtocol, vector_db_factory)  # type: ignore[type-abstract]"""

new_vector_db_factory = """    def vector_db_factory() -> VectorDBProtocol:
        from src.infrastructure.vector_store import VectorDBAdapter
        store = container.resolve(VectorStoreProtocol)  # type: ignore[type-abstract]
        return VectorDBAdapter(vector_store=store)

    container.register(VectorDBProtocol, vector_db_factory)  # type: ignore[type-abstract]"""

# also remove the comments that explain why it was mocked out
dep_content = re.sub(r'# Also bind VectorDBProtocol to the same instance.*?# for now, and the Pinecone VectorDBProtocol adapter was not created as per "FallbackVectorDB in tests"\.\n', '', dep_content, flags=re.DOTALL)
dep_content = dep_content.replace(old_vector_db_factory, new_vector_db_factory)

with open("src/interfaces/dependencies.py", "w") as f:
    f.write(dep_content)
