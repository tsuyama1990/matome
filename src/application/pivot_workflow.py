import logging

import typing

if typing.TYPE_CHECKING:
    from src.application import PivotKJEngine
from src.domain_models.pivot import PivotRequestPayload
from src.interfaces.dependencies import LLMProtocol
from src.interfaces.repository import DocumentRepositoryProtocol

logger = logging.getLogger(__name__)


class PivotWorkflow:
    """Orchestrates the Pivot KJ analysis, document retrieval, and artifact generation."""

    def __init__(
        self,
        repository: DocumentRepositoryProtocol,
        pivot_engine: "PivotKJEngine",
        llm: LLMProtocol,
    ) -> None:
        self._repository = repository
        self._pivot_engine = pivot_engine
        self._llm = llm

    async def execute(
        self, document_id: str, payload: PivotRequestPayload
    ) -> dict[str, str | dict[str, list[dict[str, str]]]]:
        """Executes the Pivot workflow."""
        try:
            document = self._repository.get_document_by_id(document_id)
        except Exception as e:
            msg = f"Failed to retrieve document {document_id}"
            logger.exception(msg)
            raise ValueError(msg) from e

        if not document.chunks:
            msg = f"Document {document_id} has no chunks."
            raise ValueError(msg)

        clusters = self._pivot_engine.pivot(document.chunks, payload.axis)

        # Serialize clusters for the prompt
        cluster_text = ""
        for cluster_name, chunks in clusters.items():
            cluster_text += f"\n## Cluster: {cluster_name}\n"
            for chunk in chunks:
                cluster_text += f"- {chunk.content}\n"

        markdown_prompt = (
            "You are a system architect. Based on the following clustered requirements, "
            "generate a formal Markdown requirements document (PRD format). "
            f"Clusters:\n{cluster_text}"
        )

        mermaid_prompt = (
            "You are a system architect. Based on the following clustered requirements, "
            "generate a valid Mermaid.js sequence diagram (only output the ```mermaid block). "
            f"Clusters:\n{cluster_text}"
        )

        try:
            markdown = await self._llm.generate(markdown_prompt)
            mermaid = await self._llm.generate(mermaid_prompt)
        except Exception as e:
            msg = "Failed to generate markdown and mermaid artifacts."
            logger.exception(msg)
            raise RuntimeError(msg) from e

        serialized_clusters = {}
        for key, value in clusters.items():
            serialized_clusters[key] = [{"id": str(c.id), "content": c.content} for c in value]

        return {
            "markdown": markdown,
            "mermaid": mermaid,
            "clusters": serialized_clusters,
        }
