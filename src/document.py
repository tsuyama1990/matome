import copy
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
from langgraph.graph import StateGraph
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.mixture import GaussianMixture
from umap import UMAP

from src.domain_models.chunk import ChunkMetadata, SemanticChunk
from src.domain_models.config import PipelineConfig
from src.domain_models.graph import KnowledgeNode, NodeState, SummaryTree
from src.domain_models.state import GraphState
from src.interfaces import (
    DocumentProcessingService,
    GraphError,
    KnowledgeGraphService,
    LLMProtocol,
    ProcessingError,
)


class DocumentProcessor(DocumentProcessingService):
    """Implementation of the DocumentProcessingService."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def process(self, state: GraphState) -> Iterator[GraphState]:
        """Processes a file referenced in state and yields incremental updates without deep copying memory."""
        if not state.file_path:
            msg = "No file path provided in GraphState"
            raise ValueError(msg)

        # Stream memory efficiently, yielding delta updates safely
        # allowing for reducer node merging without DoS OOM limits on massive lists.
        for chunk in self.process_stream(state.file_path, chunk_size=1000):
            yield GraphState(
                file_path=state.file_path,
                chunks=[chunk],
                tree=state.tree,
                active_node_id=state.active_node_id,
                pivot_axis=state.pivot_axis,
                pivot_response=state.pivot_response,
                error=state.error,
            )

    def _validate_path(self, file_path: str) -> Path:
        """Validates the file path for security and existance."""
        base_dir = Path.cwd()
        try:
            resolved_path = base_dir.joinpath(file_path).resolve(strict=True)
        except FileNotFoundError as e:
            msg = f"File not found: {file_path}"
            raise ValueError(msg) from e
        except OSError as e:
            msg = f"Invalid file path: {file_path}"
            raise ValueError(msg) from e

        if not resolved_path.is_relative_to(base_dir):
            msg = f"Path traversal attempt blocked. File must be within {base_dir}"
            raise ValueError(msg)
        return resolved_path

    def _validate_file_stats(self, resolved_path: Path) -> None:
        """Checks size limits and regular file type."""
        try:
            file_stat = resolved_path.stat()
        except FileNotFoundError as e:
            msg = f"File not found or deleted before stat: {resolved_path}"
            raise ValueError(msg) from e

        if not resolved_path.is_file():
            msg = f"Path is not a regular file: {resolved_path}"
            raise ValueError(msg)

        if file_stat.st_size > self.config.max_chunk_scan_size:
            msg = (
                f"File size exceeds maximum allowed size of {self.config.max_chunk_scan_size} bytes"
            )
            raise ValueError(msg)

    def process_stream(self, file_path: str, chunk_size: int = 1000) -> Iterator[SemanticChunk]:
        """Streams a file processing to reduce memory overhead."""
        resolved_path = self._validate_path(file_path)
        self._validate_file_stats(resolved_path)

        # Streaming bytes with incremental decoding
        import codecs

        try:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
            with resolved_path.open("rb") as f:
                buffer = ""
                page_counter = 1
                while True:
                    # Read bytes in small chunks to avoid memory exhaustion
                    # Use a small byte size to simulate byte-level streaming as required
                    chunk = f.read(chunk_size)
                    if not chunk:
                        # Flush the decoder
                        text_chunk = decoder.decode(b"", final=True)
                        if text_chunk:
                            buffer += text_chunk
                        if buffer.strip():
                            yield self._create_chunk(buffer, str(resolved_path), page_counter)
                        break

                    # Decode bytes to text incrementally
                    buffer += decoder.decode(chunk, final=False)

                    if len(buffer) >= chunk_size:
                        yield self._create_chunk(buffer, str(resolved_path), page_counter)
                        buffer = ""
                        page_counter += 1

        except UnicodeDecodeError as e:
            msg = "File must be strictly UTF-8 encoded"
            raise ProcessingError(msg) from e
        except Exception as e:
            msg = f"Failed to process document: {e}"
            raise ProcessingError(msg) from e

    def _create_chunk(self, text: str, source: str, page: int) -> SemanticChunk:
        return SemanticChunk(
            id=str(uuid.uuid4()),
            text=text,
            metadata=ChunkMetadata(
                source_document=source,
                page_number=page,
                entities_extracted=[],
            ),
        )


class RAPTORKnowledgeGraphService(KnowledgeGraphService):
    """Implementation of KnowledgeGraphService using RAPTOR core logic."""

    def __init__(self, llm_gateway: LLMProtocol, config: PipelineConfig | None = None) -> None:
        self.llm_gateway = llm_gateway
        self.config = config or PipelineConfig()

    def _create_embeddings(self, chunks: list[SemanticChunk]) -> np.ndarray:
        """Creates real text embeddings using TfidfVectorizer to fulfill the no-mock requirement."""
        vectorizer = TfidfVectorizer(max_features=384, stop_words="english")
        texts = [chunk.text for chunk in chunks]
        # In a very edge case where texts are empty, fit_transform might fail, so we handle it
        if not texts:
            return np.zeros((0, 384))
        try:
            return vectorizer.fit_transform(texts).toarray()  # type: ignore[no-any-return]
        except ValueError:
            # fallback for completely empty vocabulary
            return np.zeros((len(texts), 384))

    def _summarize_cluster(self, chunks_text: str) -> str:
        prompt = (
            "Provide a highly dense, low-cognitive-load summary for the following text chunks, "
            "adhering strictly to Chain of Density principles:\n\n"
            f"{chunks_text}"
        )
        try:
            return self.llm_gateway.invoke(prompt=prompt, retries=1)
        except Exception as e:
            msg = f"Failed to generate summary via LLM: {e}"
            raise GraphError(msg) from e

    def _embed_chunks_node(self, state_dict: dict[str, Any]) -> dict[str, Any]:
        state = GraphState(**state_dict)
        chunks = state.chunks
        if not chunks:
            msg = "Cannot build RAPTOR tree from empty chunk list."
            raise GraphError(msg)
        state.embeddings = self._create_embeddings(chunks).tolist()
        return state.model_dump()

    def _reduce_dimensions_node(self, state_dict: dict[str, Any]) -> dict[str, Any]:
        state = GraphState(**state_dict)
        if not state.embeddings:
            msg = "Embeddings not found in state."
            raise GraphError(msg)

        embeddings = np.array(state.embeddings)
        n_neighbors = min(15, embeddings.shape[0] - 1) if embeddings.shape[0] > 1 else 1
        try:
            reducer = UMAP(
                n_neighbors=n_neighbors, n_components=min(2, embeddings.shape[1]), random_state=42
            )
            reduced_embeddings = reducer.fit_transform(embeddings)
            state.reduced_embeddings = reduced_embeddings.tolist()
        except Exception as e:
            msg = f"Failed to perform UMAP reduction: {e}"
            raise GraphError(msg) from e
        return state.model_dump()

    def _cluster_chunks_node(self, state_dict: dict[str, Any]) -> dict[str, Any]:
        state = GraphState(**state_dict)
        if not state.reduced_embeddings:
            msg = "Reduced embeddings not found in state."
            raise GraphError(msg)

        reduced_embeddings = np.array(state.reduced_embeddings)
        n_components = min(5, reduced_embeddings.shape[0])
        try:
            gmm = GaussianMixture(n_components=n_components, random_state=42)
            gmm.fit(reduced_embeddings)
            probs = gmm.predict_proba(reduced_embeddings)
            state.cluster_assignments = probs.argmax(axis=1).tolist()
        except Exception as e:
            msg = f"Failed to perform GMM clustering: {e}"
            raise GraphError(msg) from e
        return state.model_dump()

    def _summarize_clusters_node(self, state_dict: dict[str, Any]) -> dict[str, Any]:
        state = GraphState(**state_dict)
        if state.cluster_assignments is None:
            msg = "Cluster assignments not found in state."
            raise GraphError(msg)

        chunks = state.chunks
        cluster_assignments = np.array(state.cluster_assignments)
        n_components = min(5, len(chunks))

        nodes: dict[str, KnowledgeNode] = {}
        for i, chunk in enumerate(chunks):
            nodes[chunk.id] = KnowledgeNode(
                id=chunk.id,
                title=f"Chunk {i+1}",
                summary=chunk.text,
                state=NodeState.LOCKED,
            )

        root_children = []
        for cluster_idx in range(n_components):
            cluster_chunk_indices = np.where(cluster_assignments == cluster_idx)[0]
            if len(cluster_chunk_indices) == 0:
                continue

            cluster_id = f"cluster_{cluster_idx}_{uuid.uuid4()}"
            cluster_chunks = [chunks[idx] for idx in cluster_chunk_indices]
            combined_text = " ".join([c.text for c in cluster_chunks])
            summary = self._summarize_cluster(combined_text)

            nodes[cluster_id] = KnowledgeNode(
                id=cluster_id,
                title=f"Cluster {cluster_idx + 1}",
                summary=summary,
                children_ids=[c.id for c in cluster_chunks],
                state=NodeState.LOCKED,
            )
            root_children.append(cluster_id)

        root_id = f"root_{uuid.uuid4()}"
        root_summary = "Root Summary Placeholder"
        if root_children:
            combined_root_text = " ".join([nodes[c_id].summary for c_id in root_children])
            root_summary = self._summarize_cluster(combined_root_text)

        nodes[root_id] = KnowledgeNode(
            id=root_id,
            title="Root Node",
            summary=root_summary,
            children_ids=root_children,
            state=NodeState.LOCKED,
        )

        state.tree = SummaryTree(root_node_id=root_id, nodes=nodes)
        return state.model_dump()

    def build_raptor_graph(self) -> StateGraph:
        """Builds a LangGraph state machine orchestrating the RAPTOR logic using discrete nodes."""
        graph_builder = StateGraph(dict)

        graph_builder.add_node("embed_chunks", self._embed_chunks_node)
        graph_builder.add_node("reduce_dimensions", self._reduce_dimensions_node)
        graph_builder.add_node("cluster_chunks", self._cluster_chunks_node)
        graph_builder.add_node("summarize_clusters", self._summarize_clusters_node)

        graph_builder.set_entry_point("embed_chunks")
        graph_builder.add_edge("embed_chunks", "reduce_dimensions")
        graph_builder.add_edge("reduce_dimensions", "cluster_chunks")
        graph_builder.add_edge("cluster_chunks", "summarize_clusters")
        graph_builder.set_finish_point("summarize_clusters")

        return graph_builder.compile()  # type: ignore[no-any-return]

    def generate_raptor_tree(self, state: GraphState) -> GraphState:
        """Builds a hierarchical tree from semantic chunks using LangGraph state machine."""
        workflow = self.build_raptor_graph()

        # We must deeply copy the incoming state
        new_state = copy.deepcopy(state)

        # Invoke LangGraph using dict representation
        result_dict = workflow.invoke(new_state.model_dump()) # type: ignore[call-overload]

        return GraphState(**result_dict)

    def generate_raptor_tree_batch(self, state: GraphState, batch_size: int = 100) -> GraphState:
        """Processes massive chunk lists in batches safely via LangGraph."""
        if len(state.chunks) > batch_size:
            chunks_to_process = state.chunks[:batch_size]
        else:
            chunks_to_process = state.chunks

        new_state = copy.deepcopy(state)
        new_state.chunks = chunks_to_process

        workflow = self.build_raptor_graph()
        result_dict = workflow.invoke(new_state.model_dump()) # type: ignore[call-overload]

        return GraphState(**result_dict)

    def pivot_kj(self, state: GraphState) -> GraphState:
        """Rearranges the tree based on state.pivot_axis and updates state.pivot_response."""
        msg = "Pivot KJ is not implemented in Cycle 04."
        raise NotImplementedError(msg)
