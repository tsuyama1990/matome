import logging
import math
import sys
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
        transport = httpx.HTTPTransport(retries=3)
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Api-Key": self.api_key},
            limits=limits,
            timeout=30.0,
            transport=transport,
        )

    def _validate_collection_name(self, collection_name: str) -> None:
        import re
        # Extremely strict whitelist: alphanumeric and underscores/hyphens only, tight length constraint
        if not re.match(r"^[a-zA-Z0-9_-]{3,63}$", collection_name):
            msg = "Invalid collection name"
            raise ValueError(msg)

    def upsert(self, collection_name: str, records: list[dict[str, Any]]) -> None:
        """Upserts records into Pinecone. Note that collection_name usually maps to namespace in Pinecone."""
        self._validate_collection_name(collection_name)

        formatted_records = []
        import html
        for r in records:
            if "id" not in r or "embedding" not in r:
                msg = "Record missing required fields 'id' or 'embedding'."
                logger.error(msg)
                raise ValueError(msg)

            # Sanitize metadata to prevent NoSQL injection via metadata payloads
            sanitized_metadata: dict[str, Any] = {}
            for k, v in r.items():
                if k in ("id", "embedding"):
                    continue
                if isinstance(v, str):
                    sanitized_metadata[k] = html.escape(v)
                elif isinstance(v, list) and all(isinstance(i, str) for i in v):
                    sanitized_metadata[k] = [html.escape(i) for i in v]
                else:
                    sanitized_metadata[k] = v

            formatted_records.append({
                "id": r["id"],
                "values": r["embedding"],
                "metadata": sanitized_metadata,
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
        self._validate_collection_name(collection_name)
        if len(query_vector) > 3072:
            msg = 'Embedding too large'
            raise ValueError(msg)

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

    MAX_MEMORY = 100 * 1024 * 1024

    def __init__(self) -> None:
        self._collections: dict[str, list[dict[str, Any]]] = {}

    def _check_memory_usage(self) -> None:
        if sys.getsizeof(self._collections) > self.MAX_MEMORY:
            logger.warning("InMemoryVectorStore exceeded max memory limit. Clearing collections.")
            self._collections.clear()

    def _validate_collection_name(self, collection_name: str) -> None:
        import re
        if not re.match(r"^[a-zA-Z0-9_-]{3,63}$", collection_name):
            msg = "Invalid collection name"
            raise ValueError(msg)

    def upsert(self, collection_name: str, records: list[dict[str, Any]]) -> None:
        self._check_memory_usage()
        self._validate_collection_name(collection_name)

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
        self._validate_collection_name(collection_name)
        if len(query_vector) > 3072:
            msg = 'Embedding too large'
            raise ValueError(msg)

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
