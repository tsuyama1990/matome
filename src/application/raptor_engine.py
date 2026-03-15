import asyncio
import logging
import uuid
from typing import Any

import numpy as np

from src.domain_models.document import RaptorNode, SemanticChunk
from src.domain_models.exceptions import RaptorError
from src.interfaces.clustering import ClusteringStrategy
from src.interfaces.llm_protocol import LLMProtocol

logger = logging.getLogger(__name__)


class RaptorEngine:
    """
    The core application service for building the RAPTOR tree.
    Builds the tree bottom-up by clustering chunks, summarizing them, and returning the RaptorNodes.
    """

    def __init__(
        self, llm: LLMProtocol, clustering_strategy: ClusteringStrategy, max_clusters: int = 10
    ) -> None:
        self.llm = llm
        self.clustering_strategy = clustering_strategy
        self.max_clusters = max_clusters

    async def _generate_cod_summary(self, text: str) -> str:
        """Helper method to generate Chain of Density summary using LLMProtocol."""
        if not text or not text.strip():
            msg = "Texts cannot be empty or contain only whitespace."
            raise ValueError(msg)

        from src.config.settings import AppConfig

        max_content_length = AppConfig().max_content_length
        if len(text) > max_content_length:
            msg = "Text chunk too large."
            raise ValueError(msg)

        prompt = (
            "Summarize this text. Then, iteratively rewrite the summary 3 times, "
            "each time adding 2 missing entities while keeping the length identical. "
            f"Text:\n{text}"
        )
        try:
            summary = await self.llm.generate_text(prompt, model="default")
            return summary.strip()
        except Exception as e:
            msg = "Failed to summarize cluster."
            raise RaptorError(msg) from e

    async def build_tree(self, chunks: list[SemanticChunk]) -> list[RaptorNode]:
        """Builds a RAPTOR hierarchical tree from chunks using SemanticClusterer."""
        if not chunks:
            return []

        embeddings = np.array([c.embedding for c in chunks], dtype=np.float32)

        # 1. Cluster embeddings
        clusters = self.clustering_strategy.cluster(embeddings, self.max_clusters)

        nodes: list[RaptorNode] = []
        cluster_tasks: list[Any] = []
        cluster_info: list[dict[str, Any]] = []

        # 2. Iterate and concatenate texts
        for _cluster_id, indices in clusters.items():
            if not indices:
                continue

            cluster_texts = [chunks[i].content for i in indices]
            child_ids = [str(chunks[i].id) for i in indices]
            combined_text = "\n".join(cluster_texts)

            cluster_tasks.append(self._generate_cod_summary(combined_text))
            cluster_info.append({"child_ids": child_ids})

        if not cluster_tasks:
            return []

        # 3. Use asyncio.gather to summarize in parallel
        summaries = await asyncio.gather(*cluster_tasks)

        # 4. Create RaptorNode objects
        for summary, info in zip(summaries, cluster_info, strict=False):
            node = RaptorNode(
                node_id=str(uuid.uuid4()),
                level=0,  # Base level of summaries over chunks
                children_ids=info["child_ids"],
                summarized_content=summary,
                is_unlocked=False,
            )
            nodes.append(node)

        return nodes
