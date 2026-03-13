import logging
import math
from typing import Any

import httpx

from src.interfaces.dependencies import VectorStoreProtocol

logger = logging.getLogger(__name__)


class PineconeVectorStore(VectorStoreProtocol):
    """
    A production-ready Pinecone client wrapping the VectorStoreProtocol using httpx
    for connection pooling and proper API interactions.
    """

    def __init__(self, api_key: str, environment: str, index_name: str) -> None:
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.base_url = f"https://{self.index_name}-{self.environment}.pinecone.io"

        # Proper connection pooling
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Api-Key": self.api_key},
            limits=limits,
            timeout=30.0,
        )

    def upsert(self, collection_name: str, records: list[dict[str, Any]]) -> None:
        """Upserts records into Pinecone. Note that collection_name usually maps to namespace in Pinecone."""
        formatted_records = []
        for r in records:
            if "id" not in r or "embedding" not in r:
                msg = "Record missing required fields 'id' or 'embedding'."
                logger.error(msg)
                raise ValueError(msg)
            formatted_records.append({
                "id": r["id"],
                "values": r["embedding"],
                "metadata": {k: v for k, v in r.items() if k not in ("id", "embedding")},
            })

        response = self.client.post(
            "/vectors/upsert",
            json={"vectors": formatted_records, "namespace": collection_name},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            msg = "Failed to upsert to Pinecone."
            logger.exception(msg)
            raise RuntimeError(msg) from e

    def search(
        self, collection_name: str, query_vector: list[float], limit: int
    ) -> list[dict[str, Any]]:
        """Searches Pinecone index."""
        response = self.client.post(
            "/query",
            json={
                "vector": query_vector,
                "topK": limit,
                "namespace": collection_name,
                "includeMetadata": True,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            msg = "Failed to query Pinecone."
            logger.exception(msg)
            raise RuntimeError(msg) from e

        data = response.json()
        results = []
        for match in data.get("matches", []):
            res = {"id": match["id"], "score": match.get("score")}
            if "metadata" in match:
                res.update(match["metadata"])
            results.append(res)

        return results

    def close(self) -> None:
        """Closes the underlying HTTP client."""
        self.client.close()


class InMemoryVectorStore(VectorStoreProtocol):
    """An in-memory implementation of VectorStoreProtocol for testing/foundational use."""

    def __init__(self) -> None:
        self._collections: dict[str, list[dict[str, Any]]] = {}

    def upsert(self, collection_name: str, records: list[dict[str, Any]]) -> None:
        if collection_name not in self._collections:
            self._collections[collection_name] = []

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
        if collection_name not in self._collections:
            return []

        records = self._collections[collection_name]

        scored_records = []
        for r in records:
            emb = r.get("embedding")
            if not emb or not query_vector:
                scored_records.append((0.0, r))
                continue

            dot_product = sum(a * b for a, b in zip(emb, query_vector, strict=False))
            mag_a = math.sqrt(sum(a * a for a in emb))
            mag_b = math.sqrt(sum(b * b for b in query_vector))
            similarity = 0.0 if mag_a == 0 or mag_b == 0 else dot_product / (mag_a * mag_b)

            scored_records.append((similarity, r))

        scored_records.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored_records[:limit]]
