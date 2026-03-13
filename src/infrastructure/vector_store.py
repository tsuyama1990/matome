import math
from typing import Any

from src.interfaces.dependencies import VectorStoreProtocol


class InMemoryVectorStore(VectorStoreProtocol):
    """An in-memory implementation of VectorStoreProtocol for testing/foundational use."""

    def __init__(self) -> None:
        # map collection_name to list of dicts
        self._collections: dict[str, list[dict[str, Any]]] = {}

    def upsert(self, collection_name: str, records: list[dict[str, Any]]) -> None:
        """Upserts records into a collection."""
        if collection_name not in self._collections:
            self._collections[collection_name] = []

        # For an in-memory test store, we just replace records if they exist or append.
        # Since records likely have an 'id', we emulate upsert.
        for record in records:
            if "id" not in record:
                self._collections[collection_name].append(record)
                continue

            idx_to_update = -1
            for i, existing in enumerate(self._collections[collection_name]):
                if existing.get("id") == record["id"]:
                    idx_to_update = i
                    break

            if idx_to_update != -1:
                self._collections[collection_name][idx_to_update] = record
            else:
                self._collections[collection_name].append(record)

    def search(
        self, collection_name: str, query_vector: list[float], limit: int
    ) -> list[dict[str, Any]]:
        """Searches for records using a simple cosine similarity or returning limited results."""
        if collection_name not in self._collections:
            return []

        records = self._collections[collection_name]

        # Calculate cosine similarity if embeddings exist
        scored_records = []
        for r in records:
            emb = r.get("embedding")
            if not emb or not query_vector:
                scored_records.append((0.0, r))
                continue

            # Cosine similarity
            dot_product = sum(a * b for a, b in zip(emb, query_vector, strict=False))
            mag_a = math.sqrt(sum(a * a for a in emb))
            mag_b = math.sqrt(sum(b * b for b in query_vector))
            similarity = 0.0 if mag_a == 0 or mag_b == 0 else dot_product / (mag_a * mag_b)

            scored_records.append((similarity, r))

        scored_records.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored_records[:limit]]
