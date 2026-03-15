import json
import logging
import typing
import uuid

if typing.TYPE_CHECKING:
    pass


from tenacity import retry, stop_after_attempt, wait_exponential

from src.domain_models.document import EnrichedDocument, SemanticChunk
from src.domain_models.pivot import PivotNode, PivotRequestPayload, PivotState
from src.interfaces.dependencies import EmbeddingProtocol, LLMProtocol, VectorDBProtocol
from src.interfaces.repository import DocumentRepositoryProtocol

logger = logging.getLogger(__name__)


class PivotGenerationError(Exception):
    """Domain exception for when the Pivot Engine fails to orchestrate or parse."""


class PivotEngine:
    """Core service for knowledge reconstruction based on Multi-Dimensional axes."""

    def __init__(
        self, llm: LLMProtocol, vector_db: VectorDBProtocol, embedding: EmbeddingProtocol
    ) -> None:
        self._llm = llm
        self._vector_db = vector_db
        self._embedding = embedding

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _retrieve_chunks(self, document: EnrichedDocument, axis: str) -> list[SemanticChunk]:
        """Retrieves and filters chunks based on the requested axis."""
        axis_embedding = await self._embedding.embed_text(axis)

        filter_metadata: dict[str, str] | None = None
        if "actor" in axis.lower():
            filter_metadata = {"axis_type": "actor_axis"}
        elif "time" in axis.lower():
            filter_metadata = {"axis_type": "time_axis"}

        try:
            chunks = await self._vector_db.search(
                query_embedding=axis_embedding, top_k=20, filter_metadata=filter_metadata
            )
        except Exception as e:
            msg = "Failed to query Vector Database."
            raise PivotGenerationError(msg) from e

        if not chunks:
            chunks = document.chunks[:20]

        if not chunks:
            msg = "No chunks available for Pivot processing."
            raise PivotGenerationError(msg)

        return chunks

    async def execute_pivot(self, document: EnrichedDocument, axis: str) -> PivotState:
        """
        Executes the Pivot analysis using Vector search and LLM synthesis.
        """
        import asyncio
        import re

        # Sanitize and validate axis parameter
        sanitized_axis = axis.strip().lower()
        if not re.match(r"^[a-zA-Z0-9\s_-]+$", sanitized_axis):
            msg = "Invalid axis format. Allowed characters are alphanumeric, spaces, dashes, or underscores."
            raise PivotGenerationError(msg)

        chunks = await self._retrieve_chunks(document, sanitized_axis)

        if not chunks:
            msg = "No chunks available for Pivot processing."
            raise PivotGenerationError(msg)

        chunk_context = "".join([f"Chunk ID: {c.id}\nContent: {c.content}\n---\n" for c in chunks])

        prompt = (
            f"Analyze these text chunks. Organize them into the conceptual axis: '{axis}'.\n"
            "Identify distinct categories or concepts based on this axis.\n"
            "Return ONLY a strictly formatted JSON object matching this schema:\n"
            "{\n"
            '  "nodes": [\n'
            "    {\n"
            '      "label": "Name of the category/concept",\n'
            '      "summary": "Detailed summary",\n'
            '      "source_chunk_ids": ["uuid1", "uuid2"]\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Chunks:\n"
            f"{chunk_context}"
        )

        try:
            # Add timeout protection for LLM call
            response_json = await asyncio.wait_for(self._llm.generate(prompt), timeout=60.0)
            response_json = response_json.replace("```json", "").replace("```", "").strip()
            data = json.loads(response_json)

            nodes = []
            for node_data in data.get("nodes", []):
                node_data["node_id"] = str(uuid.uuid4())

                # Extract chunk IDs safely, validating they are valid UUID strings
                valid_chunk_ids = []
                for uid in node_data.get("source_chunk_ids", []):
                    import contextlib
                    with contextlib.suppress(ValueError, TypeError, AttributeError):
                        valid_chunk_ids.append(uuid.UUID(uid))
                node_data["source_chunk_ids"] = valid_chunk_ids
                nodes.append(PivotNode(**node_data))

        except json.JSONDecodeError as e:
            logger.exception("Failed to parse LLM JSON output.")
            msg = "LLM returned malformed JSON."
            raise PivotGenerationError(msg) from e
        except TimeoutError as e:
            logger.exception("LLM pivot generation timed out.")
            msg = "LLM pivot generation timed out."
            raise PivotGenerationError(msg) from e
        except Exception as e:
            logger.exception("Failed to generate Pivot state.")
            msg = "Failed to generate Pivot state due to invalid LLM format or constraints."
            raise PivotGenerationError(msg) from e
        else:
            state = PivotState(
                original_document_id=document.document_id, axis_name=sanitized_axis, nodes=nodes
            )
            logger.info(f"Successfully generated PivotState for axis: {sanitized_axis}")
            return state


class ExportService:
    """Service to export Pivot states into readable formats."""

    def generate_markdown(self, state: PivotState) -> str:
        """Converts the PivotState into a Markdown document."""
        if not state.nodes:
            return f"# {state.axis_name}\n\nNo structured concepts were found for this axis."

        lines = [f"# {state.axis_name}"]
        lines.append("")

        for node in state.nodes:
            if not node:
                continue
            lines.append(f"## {node.label}")
            lines.append(node.summary)
            lines.append("")

        return "\n".join(lines)


class PivotWorkflow:
    """Orchestrates the Pivot KJ analysis, document retrieval, and artifact generation."""

    def __init__(
        self,
        repository: DocumentRepositoryProtocol,
        pivot_engine: PivotEngine,
        llm: LLMProtocol,
    ) -> None:
        self._repository = repository
        self._pivot_engine = pivot_engine
        self._llm = llm

    async def execute(
        self, document_id: uuid.UUID, payload: PivotRequestPayload
    ) -> dict[str, typing.Any]:
        """Executes the Pivot workflow."""
        try:
            document = self._repository.get_document_by_id(str(document_id))
        except Exception as e:
            msg = f"Failed to retrieve document {document_id}"
            logger.exception(msg)
            raise ValueError(msg) from e

        if not document.chunks:
            msg = f"Document {document_id} has no chunks."
            raise ValueError(msg)

        # 1. Reconstruct knowledge via Pivot Engine
        pivot_state = await self._pivot_engine.execute_pivot(document, payload.axis)

        # 2. Serialize clusters for the prompt based on PivotState
        cluster_text = ""
        for node in pivot_state.nodes:
            cluster_text += f"\n## Cluster: {node.label}\n"
            cluster_text += f"Summary: {node.summary}\n"

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

        markdown = "Markdown generation failed."
        mermaid = "Mermaid generation failed."

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        )
        async def generate_artifact(prompt: str) -> str:
            return await self._llm.generate(prompt)

        try:
            markdown = await generate_artifact(markdown_prompt)
        except Exception:
            logger.exception(
                "Failed to generate markdown artifact, continuing with partial success."
            )

        try:
            mermaid = await generate_artifact(mermaid_prompt)
        except Exception:
            logger.exception(
                "Failed to generate mermaid artifact, continuing with partial success."
            )

        serialized_clusters = {}
        for node in pivot_state.nodes:
            # We don't have the original chunk content directly on the node without mapping back to document.chunks
            # But we can serialize the source_chunk_ids
            serialized_clusters[node.label] = [{"id": str(chunk_id)} for chunk_id in node.source_chunk_ids]

        return {
            "markdown": markdown,
            "mermaid": mermaid,
            "clusters": serialized_clusters,
        }
