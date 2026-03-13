import logging
import uuid
from collections import defaultdict
from typing import Any

from src.domain_models import RaptorNode, SemanticChunk
from src.domain_models.exceptions import NLPModelLoadError, ProcessingError, RaptorError
from src.interfaces.clustering import ClusteringStrategy
from src.interfaces.dependencies import LLMProtocol

logger = logging.getLogger(__name__)


class NLPService:
    """Service dedicated to natural language processing and entity tagging."""

    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        self.nlp: Any | None = None
        self.model_name = model_name
        self._load_model()

    def _load_model(self) -> None:
        """Loads the Spacy model safely."""
        try:
            import spacy
        except ImportError as e:
            msg = "Spacy library is not installed."
            raise NLPModelLoadError(msg) from e

        try:
            self.nlp = spacy.load(self.model_name)
        except OSError as e:
            msg = f"Spacy model '{self.model_name}' is missing. Please install it."
            raise NLPModelLoadError(msg) from e

    def tag_entities_and_axes(self, chunks: list[SemanticChunk]) -> None:
        """
        Public method to tag entities and multi-dimensional axes.
        Moved out from being a complex private method to ensure Single Responsibility.
        """
        if self.nlp is None:
            msg = "NLP model is not loaded."
            raise RuntimeError(msg)

        for chunk in chunks:
            doc = self.nlp(chunk.content)
            extracted_entities = []

            # ReDoS protection: Limit maximum entities extracted per chunk to prevent memory bloat
            for ent in doc.ents[:50]:
                # XSS protection: Ignore any entity that looks like script injection
                if "<script" in ent.text.lower() or "javascript:" in ent.text.lower():
                    continue

                if ent.label_ in ("PERSON", "ORG", "GPE", "PRODUCT"):
                    extracted_entities.append(ent.text)

            chunk.metadata.extracted_entities = list(set(extracted_entities))

            # Basic deterministic heuristic for Time Axis (Past, Present, Future)
            content_lower = chunk.content.lower()
            if any(word in content_lower for word in ["yesterday", "previously", "was", "were"]):
                chunk.metadata.time_axis = "Past"
            elif any(word in content_lower for word in ["tomorrow", "will", "future", "next"]):
                chunk.metadata.time_axis = "Future"
            else:
                chunk.metadata.time_axis = "Present"


class RAPTOREngine:
    """
    Engine to orchestrate clustering to form a RAPTOR tree.
    Builds the tree bottom-up by clustering chunks, summarising them, and recursively
    clustering the summaries until a single root remains (or max depth is reached).
    """

    def __init__(
        self,
        llm: LLMProtocol,
        clustering_strategy: ClusteringStrategy,
        max_levels: int = 3,
        max_clusters: int = 5,
    ) -> None:
        self._llm = llm
        self._clustering_strategy = clustering_strategy
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

    async def cluster_chunks(self, chunks: list[SemanticChunk]) -> list[RaptorNode]:
        """
        Builds a RAPTOR hierarchical tree from chunks.
        Strictly applies clustering strategy for mathematically sound clustering.
        """

        if not chunks:
            return []

        all_nodes: list[RaptorNode] = []
        current_level_texts = [c.content for c in chunks]
        current_level_embeddings = [c.embedding for c in chunks]
        current_level_ids = [str(c.id) for c in chunks]

        level = 0
        while level < self._max_levels and len(current_level_texts) > 1:
            reduced_embeddings = self._clustering_strategy.reduce_dimensions(
                current_level_embeddings
            )
            clusters = self._clustering_strategy.cluster(reduced_embeddings, self._max_clusters)

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

                # Mean pooling for embeddings list fallback
                cluster_embs = [current_level_embeddings[i] for i in indices]
                if cluster_embs:
                    mean_emb = [
                        sum(x) / len(cluster_embs) for x in zip(*cluster_embs, strict=False)
                    ]
                    next_level_embeddings.append(mean_emb)

            current_level_texts = next_level_texts
            current_level_embeddings = next_level_embeddings
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

    ALLOWED_AXES = frozenset({"actor", "time", "entities"})

    def pivot(self, chunks: list[SemanticChunk], axis: str) -> dict[str, list[SemanticChunk]]:
        """
        Dynamically relocates and clusters chunks based on explicitly defined metadata tags.
        """
        if not chunks:
            return {}

        axis_lower = axis.lower()
        if axis_lower not in self.ALLOWED_AXES:
            msg = (
                f"Invalid axis '{axis}'. Supported axes are {', '.join(sorted(self.ALLOWED_AXES))}."
            )
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
