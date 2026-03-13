"""
Application layer containing orchestration workflows, use cases, and AI services.
"""

import re
import uuid
from typing import Any

import numpy as np
import spacy
import umap
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from sentence_transformers import SentenceTransformer
from sklearn.mixture import GaussianMixture

from src.config.settings import ModelConfig
from src.domain_models.document import ChunkMetadata, RaptorNode, SemanticChunk
from src.domain_models.exceptions import DependencyError, ProcessingError
from src.domain_models.graph_state import GraphState, ProcessingStatus
from src.interfaces.dependencies import ChunkingProtocol, DocumentParserProtocol, LLMProtocol


class SemanticChunkingService:
    """A real semantic chunking service using cosine similarity."""

    def __init__(self, config: ModelConfig) -> None:
        self.model = SentenceTransformer(config.embedding_model)

    def chunk_text(
        self, text: str, source_file: str, threshold: float = 0.5
    ) -> list[SemanticChunk]:
        """Splits text into semantic chunks based on sentence similarity."""
        if not text:
            msg = "Cannot chunk empty text."
            raise ProcessingError(msg)

        # Basic sentence splitting (using spacy would be better, but re is fallback)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return []

        embeddings = self.model.encode(sentences)

        chunks: list[SemanticChunk] = []
        current_chunk_sentences = [sentences[0]]

        for i in range(1, len(sentences)):
            # Calculate cosine similarity
            sim = np.dot(embeddings[i - 1], embeddings[i]) / (
                np.linalg.norm(embeddings[i - 1]) * np.linalg.norm(embeddings[i])
            )

            # If similarity drops below threshold, we found a semantic boundary
            if sim < threshold:
                content = " ".join(current_chunk_sentences)
                if content:
                    metadata = ChunkMetadata(source_file=source_file, page_number=len(chunks) + 1)
                    chunks.append(
                        SemanticChunk(
                            id=uuid.uuid4(),
                            content=content,
                            metadata=metadata,
                        )
                    )
                current_chunk_sentences = [sentences[i]]
            else:
                current_chunk_sentences.append(sentences[i])

        # Add the last chunk
        if current_chunk_sentences:
            content = " ".join(current_chunk_sentences)
            if content:
                metadata = ChunkMetadata(source_file=source_file, page_number=len(chunks) + 1)
                chunks.append(
                    SemanticChunk(
                        id=uuid.uuid4(),
                        content=content,
                        metadata=metadata,
                    )
                )

        return chunks


class EmbeddingAndClusteringService:
    """Service to generate embeddings and cluster chunks using UMAP and GMM."""

    def __init__(self, config: ModelConfig) -> None:
        self.model = SentenceTransformer(config.embedding_model)

        # Load spacy strictly once during singleton initialization to prevent massive memory leaks
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            from spacy.cli.download import download

            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

    def embed_and_cluster(self, chunks: list[SemanticChunk]) -> dict[int, list[str]]:
        """Embeds chunks, reduces dimensionality via UMAP, and clusters with GMM."""
        if not chunks:
            return {}

        contents = [c.content for c in chunks]
        embeddings = self.model.encode(contents)

        self._tag_entities_and_axes(chunks, embeddings, self.nlp)

        # We need at least 4 samples for UMAP to avoid spectral embedding errors in small test sets
        if len(embeddings) < 4:
            return {0: [str(c.id) for c in chunks]}

        # Dimensionality reduction
        n_neighbors = min(15, len(embeddings) - 1)
        reducer = umap.UMAP(n_neighbors=n_neighbors, n_components=2, random_state=42)
        reduced_embeddings = reducer.fit_transform(embeddings)

        # GMM Clustering
        n_components = min(5, len(embeddings))  # Max 5 clusters for small tests
        gmm = GaussianMixture(n_components=n_components, random_state=42)
        gmm.fit(reduced_embeddings)
        probs = gmm.predict_proba(reduced_embeddings)

        clusters: dict[int, list[str]] = {}
        for i, chunk in enumerate(chunks):
            # Soft clustering: assign chunk to clusters where probability > threshold
            for cluster_id, prob in enumerate(probs[i]):
                if prob > 0.1:  # Assign to cluster
                    if cluster_id not in clusters:
                        clusters[cluster_id] = []
                    clusters[cluster_id].append(str(chunk.id))
        return clusters

    def _tag_entities_and_axes(
        self, chunks: list[SemanticChunk], embeddings: Any, nlp: Any
    ) -> None:
        """Helper to tag chunks and manage embeddings to reduce function complexity."""
        for i, chunk in enumerate(chunks):
            # Perform NER via spacy
            doc = nlp(chunk.content)
            chunk.metadata.extracted_entities = list({ent.text for ent in doc.ents})

            # Real axis tagging based on NLP part-of-speech (POS) and dependency parsing
            # Time axis: Find verb tenses to define temporal axis
            past_verbs = sum(1 for token in doc if token.tag_ in ("VBD", "VBN"))
            future_verbs = sum(
                1
                for token in doc
                if token.tag_ == "MD" and token.text.lower() in ("will", "shall", "would")
            )

            if future_verbs > past_verbs:
                chunk.metadata.time_axis = "Future"
            elif past_verbs > future_verbs:
                chunk.metadata.time_axis = "Past"
            else:
                chunk.metadata.time_axis = "Present"

            # Actor axis: Find the main subject (nsubj) to define the actor
            subjects = [token.text for token in doc if token.dep_ == "nsubj"]
            if subjects:
                chunk.metadata.actor_axis = subjects[0].capitalize()
            else:
                chunk.metadata.actor_axis = "System"

            emb = [float(x) for x in embeddings[i]]
            chunk.embedding = emb


def _validate_document_presence(state: GraphState) -> None:
    """Validates that a document is present in the state."""
    if state.current_document is None:
        msg = "Missing document."
        raise ProcessingError(msg)


def parse_file_node(state: GraphState) -> GraphState:
    """Node that parses the file into an EnrichedDocument."""
    if state.source_filepath is None:
        msg = "No source filepath provided in state."
        state.add_error(msg)
        state.transition_status(ProcessingStatus.FAILED)
        return state

    try:
        from src.application.di import global_container

        container = global_container

        try:
            parser = container.resolve(DocumentParserProtocol)  # type: ignore[type-abstract]
        except RuntimeError:
            msg = "DocumentParserProtocol not registered in DI container."
            raise DependencyError(msg) from None

        content = parser.parse(state.source_filepath)

        # Create the document containing the parsed content
        doc_id = uuid.uuid4()
        from src.domain_models.document import EnrichedDocument

        doc = EnrichedDocument(document_id=doc_id, original_text=content)
        state.current_document = doc

        state.transition_status(ProcessingStatus.CHUNKING)

    except ProcessingError as e:
        state.add_error(str(e))
        state.transition_status(ProcessingStatus.FAILED)

    return state


def embedding_and_clustering_node(state: GraphState) -> GraphState:
    """Node that handles embedding the chunks and running UMAP/GMM clustering."""
    if state.processing_status != ProcessingStatus.EMBEDDING:
        return state

    try:
        _validate_document_presence(state)

        try:
            from src.application.di import global_container

            container = global_container
            model_config = container.resolve(ModelConfig)
        except RuntimeError:
            model_config = ModelConfig()  # type: ignore[call-arg]

        service = EmbeddingAndClusteringService(model_config)
        if state.current_document is not None:
            # Note: embed_and_cluster handles both generating embeddings and the UMAP/GMM clustering logic
            # to keep the pipeline tight. It directly mutates chunks embedding vectors.
            clusters = service.embed_and_cluster(state.current_document.chunks)

            # Now we create RaptorNodes based on the soft clusters
            raptor_nodes = []
            for cluster_id, chunk_ids in clusters.items():
                node = RaptorNode(
                    node_id=f"cluster-{cluster_id}-{uuid.uuid4()}",
                    level=1,
                    children_ids=chunk_ids,
                    summarized_content="[Pending CoD Summarization]",
                )
                raptor_nodes.append(node)

            state.current_document.raptor_nodes = raptor_nodes
            state.transition_status(ProcessingStatus.CLUSTERING)
            # Instantly step to summarizing since the clustering math was done above
            state.transition_status(ProcessingStatus.SUMMARIZING)

    except ProcessingError as e:
        state.add_error(str(e))
        state.transition_status(ProcessingStatus.FAILED)

    return state


async def summarization_node(state: GraphState) -> GraphState:
    """Node that runs Chain of Density (CoD) prompting on clusters."""
    if state.processing_status != ProcessingStatus.SUMMARIZING:
        return state

    try:
        _validate_document_presence(state)

        try:
            from src.application.di import global_container

            container = global_container
            llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        except RuntimeError:
            msg = "LLMProtocol not registered in DI container."
            raise DependencyError(msg) from None

        if state.current_document is not None:
            for node in state.current_document.raptor_nodes:
                chunk_texts = [
                    c.content
                    for c in state.current_document.chunks
                    if str(c.id) in node.children_ids
                ]
                combined = " ".join(chunk_texts)
                prompt = f"Perform Chain of Density summarization on the following text to maximize entities:\n\n{combined}"

                try:
                    summary = await llm.generate(prompt)
                except Exception as llm_err:
                    summary = (
                        f"[CoD Fallback] Could not reach LLM. Content preview: {combined[:100]}..."
                    )
                    state.add_error(f"LLM failure on node {node.node_id}: {llm_err}")

                node.summarized_content = summary

            state.transition_status(ProcessingStatus.COMPLETE)

    except ProcessingError as e:
        state.add_error(str(e))
        state.transition_status(ProcessingStatus.FAILED)

    return state


def chunk_text_node(state: GraphState) -> GraphState:
    """Node that chunks the parsed text."""
    if state.processing_status != ProcessingStatus.CHUNKING:
        return state

    try:
        _validate_document_presence(state)

        try:
            from src.application.di import global_container

            container = global_container
            chunker = container.resolve(ChunkingProtocol)  # type: ignore[type-abstract]
        except RuntimeError:
            msg = "ChunkingProtocol not registered in DI container."
            raise DependencyError(msg) from None

        if state.current_document is not None:
            text = state.current_document.original_text
            source_file = str(state.current_document.document_id)

            chunks = chunker.chunk_text(text, source_file)
            state.current_document.chunks = chunks
            state.transition_status(ProcessingStatus.EMBEDDING)

    except ProcessingError as e:
        state.add_error(str(e))
        state.transition_status(ProcessingStatus.FAILED)

    return state


def build_ingestion_graph() -> CompiledStateGraph:  # type: ignore[type-arg]
    """Builds and compiles the ingestion workflow graph."""
    workflow = StateGraph(GraphState)

    workflow.add_node("parse", parse_file_node)
    workflow.add_node("chunk", chunk_text_node)
    workflow.add_node("embed", embedding_and_clustering_node)
    workflow.add_node("summarize", summarization_node)

    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "chunk")
    workflow.add_edge("chunk", "embed")
    workflow.add_edge("embed", "summarize")
    workflow.set_finish_point("summarize")

    return workflow.compile()
