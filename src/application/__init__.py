"""
Application layer containing orchestration workflows, use cases, and AI services.
"""

import contextlib
import logging
import uuid
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np

from src.domain_models.document import RaptorNode, SemanticChunk
from src.domain_models.exceptions import ProcessingError, RaptorError
from src.interfaces.dependencies import LLMProtocol

logger = logging.getLogger(__name__)

with contextlib.suppress(ImportError):
    import umap
    from sklearn.decomposition import PCA
    from sklearn.mixture import GaussianMixture

if TYPE_CHECKING:
    from spacy.language import Language


class NLPModelLoadError(Exception):
    """Custom exception when NLP models fail to load."""


class NLPService:
    """Service dedicated to natural language processing and entity tagging."""

    def __init__(self) -> None:
        self.nlp: Language | None = None
        self._load_model()

    def _load_model(self) -> None:
        """Loads the Spacy model safely."""
        try:
            import spacy
        except ImportError as e:
            msg = "Spacy library is not installed."
            raise NLPModelLoadError(msg) from e

        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError as e:
            msg = "Spacy model 'en_core_web_sm' is missing. Please install it."
            raise NLPModelLoadError(msg) from e

    def tag_entities_and_axes(self, chunks: list[SemanticChunk]) -> None:
        """
        Public method to tag entities and multi-dimensional axes.
        Moved out from being a complex private method to ensure Single Responsibility.
        """
        if self.nlp is None:
            msg = "NLP model is not loaded."
            raise RuntimeError(msg)

        # Actual implementation relying on the nlp object to extract named entities.
        for chunk in chunks:
            if chunk.content:
                doc = self.nlp(chunk.content)
                # Extract specific entity types suitable for system design/analysis
                target_labels = {"ORG", "PERSON", "GPE", "PRODUCT", "EVENT"}
                chunk.metadata.extracted_entities = [
                    ent.text for ent in doc.ents if ent.label_ in target_labels
                ]

                # Basic heuristic mapping for axes based on entities
                if any(ent.label_ in {"PERSON", "ORG"} for ent in doc.ents):
                    chunk.metadata.actor_axis = "Detected Actor"
                if any(ent.label_ in {"DATE", "TIME"} for ent in doc.ents):
                    chunk.metadata.time_axis = "Detected Time"


class RAPTOREngine:
    """
    Engine to orchestrate UMAP and GMM clustering to form a RAPTOR tree.
    Builds the tree bottom-up by clustering chunks, summarising them, and recursively
    clustering the summaries until a single root remains (or max depth is reached).
    """

    def __init__(self, llm: LLMProtocol, max_levels: int = 3, max_clusters: int = 5) -> None:
        self._llm = llm
        self._max_levels = max_levels
        self._max_clusters = max_clusters

    async def _summarize_cluster(self, texts: list[str]) -> str:
        """Summarizes a list of texts using the Chain of Density concept."""
        if not texts:
            msg = "Texts cannot be empty."
            raise ValueError(msg)

        if any(len(t) > 100000 for t in texts):
            msg = "Text chunk too large."
            raise ValueError(msg)

        combined_text = "\n".join(texts)
        prompt = (
            "Summarize the following texts into a single, highly dense paragraph. "
            "Extract the core entities and relationships. "
            f"Texts:\n{combined_text}"
        )
        try:
            summary = await self._llm.generate(prompt)
            return summary.strip()
        except Exception as e:
            msg = "Failed to summarize cluster."
            raise RaptorError(msg) from e

    def _reduce_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        if not isinstance(embeddings, np.ndarray):
            msg = f"Expected embeddings to be a numpy array, got {type(embeddings)}."
            logger.error(msg)
            raise TypeError(msg)

        if embeddings.ndim != 2:
            msg = f"Expected embeddings to be a 2D numpy array, got shape {embeddings.shape}."
            logger.error(msg)
            raise ValueError(msg)

        n_samples = len(embeddings)

        if n_samples == 0:
            return embeddings

        n_neighbors = min(15, n_samples - 1) if n_samples > 2 else 2
        n_components = min(2, n_samples)

        # Avoid running UMAP on extremely small sample sets to prevent spectral
        # initialization issues in low-dimensional space
        if n_samples > 3:
            reducer = umap.UMAP(
                n_neighbors=n_neighbors,
                n_components=n_components,
                metric="cosine",
                random_state=42,
            )
            return reducer.fit_transform(embeddings)  # type: ignore[no-any-return]

        # Use PCA as fallback to ensure a valid 2D array is returned
        # without spectral initialization issues.
        if embeddings.shape[1] > n_components:
            pca = PCA(n_components=n_components, random_state=42)
            return pca.fit_transform(embeddings)  # type: ignore[no-any-return]

        return embeddings

    def _validate_embeddings_type_and_shape(self, embeddings: np.ndarray) -> None:
        """Helper to ensure embeddings are valid 2D numpy arrays before processing."""
        if not isinstance(embeddings, np.ndarray):
            msg = f"Expected embeddings to be a numpy array, got {type(embeddings)}."
            logger.error(msg)
            raise TypeError(msg)

        if len(embeddings.shape) != 2:
            msg = f"Invalid embedding dimensions. Expected 2D array, got shape {embeddings.shape}."
            logger.error(msg)
            raise ValueError(msg)

    def _cluster_reduced_embeddings(self, embeddings: np.ndarray) -> dict[int, list[int]]:
        self._validate_embeddings_type_and_shape(embeddings)

        n_samples = len(embeddings)
        if n_samples == 0 or (n_samples == 1 and embeddings.shape[1] == 0):
            return {}

        n_clusters = min(self._max_clusters, n_samples)

        # If we have very few samples, explicitly group them to form a hierarchy
        # instead of dumping them all into a single flat cluster
        if n_samples < 3 or n_samples <= n_clusters:
            logger.warning(
                "Sample count %d is too small for GMM clustering. "
                "Using explicit fallback hierarchy grouping.", n_samples
            )
            if n_samples == 2:
                # Still cluster them separately to maintain tree generation depth if allowed
                return {0: [0], 1: [1]}
            if n_samples == 1:
                return {0: [0]}
            return {0: list(range(n_samples))}

        try:
            gmm = GaussianMixture(n_components=n_clusters, random_state=42)
            gmm.fit(embeddings)
            probs = gmm.predict_proba(embeddings)

            threshold = 0.2
            clusters = defaultdict(list)

            # Vectorized threshold assignment
            above_threshold = probs > threshold
            for i in range(n_samples):
                # Get cluster indices where prob > threshold
                assigned_clusters = np.where(above_threshold[i])[0]

                # Soft clustering: assign to all clusters above threshold
                for cluster_idx in assigned_clusters:
                    clusters[int(cluster_idx)].append(i)

                # Fallback: if no cluster meets the threshold, assign to the most probable one
                if len(assigned_clusters) == 0:
                    best_cluster = int(np.argmax(probs[i]))
                    clusters[best_cluster].append(i)

            return dict(clusters)
        except Exception:
            # Fallback if GMM fails (e.g. singular covariance matrix with duplicate points)
            logger.exception("GMM clustering failed. Falling back to singular cluster.")
            return {0: list(range(n_samples))}

    async def cluster_chunks(self, chunks: list[SemanticChunk]) -> list[RaptorNode]:
        """
        Builds a RAPTOR hierarchical tree from chunks.
        Strictly applies UMAP and GaussianMixture for mathematically sound clustering.
        """

        if not chunks:
            return []

        all_nodes: list[RaptorNode] = []
        current_level_texts = [c.content for c in chunks]
        current_level_embeddings = np.array([c.embedding for c in chunks])
        current_level_ids = [str(c.id) for c in chunks]

        level = 0
        while level < self._max_levels and len(current_level_texts) > 1:
            reduced_embeddings = self._reduce_embeddings(current_level_embeddings)
            clusters = self._cluster_reduced_embeddings(reduced_embeddings)

            next_level_texts = []
            next_level_embeddings = []
            next_level_ids = []

            for _cluster_idx, indices in clusters.items():
                if not indices:
                    continue

                cluster_texts = [current_level_texts[i] for i in indices]
                child_ids = [current_level_ids[i] for i in indices]

                summary = await self._summarize_cluster(cluster_texts)
                node_id = str(uuid.uuid4())

                node = RaptorNode(
                    node_id=node_id,
                    level=level,
                    children_ids=child_ids,
                    summarized_content=summary,
                    is_unlocked=False,
                )
                all_nodes.append(node)

                next_level_texts.append(summary)
                next_level_ids.append(node_id)

                cluster_embs = np.array([current_level_embeddings[i] for i in indices])
                next_level_embeddings.append(cluster_embs.mean(axis=0).tolist())

            current_level_texts = next_level_texts
            current_level_embeddings = np.array(next_level_embeddings)
            current_level_ids = next_level_ids
            level += 1

        return all_nodes


class SQ3REngine:
    """
    Engine for interactive Question and Recite features in the SQ3R loop.
    Generates questions to unlock nodes, and evaluates user recited summaries.
    """

    def __init__(self, llm: LLMProtocol) -> None:
        self._llm = llm

    async def generate_question(self, node: RaptorNode) -> str:
        """Generates a contextual question based on the node's hidden summary."""
        prompt = (
            "Based on the following summary, generate a single, thought-provoking question "
            "that tests the reader's understanding of the core concept. The question should "
            "not directly reveal the answer.\n\n"
            f"Summary: {node.summarized_content}\n\n"
            "Question:"
        )
        try:
            question = await self._llm.generate(prompt)
            return question.strip()
        except Exception as e:
            msg = "Failed to generate question."
            raise ProcessingError(msg) from e

    async def evaluate_answer(self, user_answer: str, node: RaptorNode) -> str:
        """Evaluates the user's answer against the node's summary, providing 'Sandwich Feedback'."""
        prompt = (
            "You are an AI tutor. A student has just read the following summary and provided an answer "
            "to a question about it. Provide 'Sandwich Feedback': "
            "1. Praise their effort.\n"
            "2. Gently correct any errors or hallucinations.\n"
            "3. Praise their overall structure and encourage them.\n\n"
            f"Original Summary: {node.summarized_content}\n"
            f"Student Answer: {user_answer}\n\n"
            "Feedback:"
        )
        try:
            feedback = await self._llm.generate(prompt)
            return feedback.strip()
        except Exception as e:
            msg = "Failed to evaluate answer."
            raise ProcessingError(msg) from e


class PivotKJEngine:
    """
    Engine to orchestrate dynamic re-clustering (Pivot KJ) of semantic chunks based
    on specific multi-dimensional axes (e.g., actor, timeline).
    """

    def pivot(self, chunks: list[SemanticChunk], axis: str) -> dict[str, list[SemanticChunk]]:
        """
        Dynamically relocates and clusters chunks based on explicitly defined metadata tags.
        """
        if not chunks:
            return {}

        axis_lower = axis.lower()
        if axis_lower not in ("actor", "time", "entities"):
            msg = f"Invalid axis '{axis}'. Supported axes are 'actor', 'time', and 'entities'."
            logger.error(msg)
            raise ValueError(msg)

        clusters: dict[str, list[SemanticChunk]] = defaultdict(list)

        for chunk in chunks:
            # Map dynamic axes to concrete metadata fields based on axis name
            target_value = "Uncategorized"

            if "actor" in axis_lower:
                target_value = chunk.metadata.actor_axis or "Uncategorized"
            elif "time" in axis_lower:
                target_value = chunk.metadata.time_axis or "Uncategorized"
            elif "entities" in axis_lower and chunk.metadata.extracted_entities:
                target_value = chunk.metadata.extracted_entities[0]

            clusters[target_value].append(chunk)

        # Convert defaultdict to standard dict for strict typing
        return dict(clusters)


__all__ = ["NLPModelLoadError", "NLPService", "PivotKJEngine", "RAPTOREngine", "SQ3REngine"]
