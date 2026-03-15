import asyncio
import json
import logging
import re
import uuid
from collections import defaultdict
from typing import Any

import bleach

from src.application.pivot_workflow import PivotWorkflow
from src.application.raptor_engine import RaptorEngine
from src.domain_models import ChunkMetadata, EnrichedDocument, RaptorNode, SemanticChunk
from src.domain_models.exceptions import NLPModelLoadError, ProcessingError
from src.interfaces.clustering import PivotEngineProtocol
from src.interfaces.dependencies import EmbeddingProtocol, LLMProtocol, TextParserProtocol

logger = logging.getLogger(__name__)


_LLM_JSON_FORMAT_PROMPT = (
    "Analyze the following text. Extract proper nouns (entities) and "
    "categorize the text along the time axis (Past, Present, or Future). "
    "Respond ONLY with a valid JSON object in the following exact format:\n"
    '{{"entities": ["Entity1", "Entity2"], "time_axis": "Present"}}\n\n'
    "Text:\n{text}"
)


class NLPService:
    """Service dedicated to natural language processing and entity tagging."""

    def __init__(
        self,
        model_name: str,
        time_axis_past_words: list[str],
        time_axis_future_words: list[str],
        max_content_length: int = 100000,
        max_entities: int = 50,
    ) -> None:
        self.max_content_length = max_content_length
        self.nlp: Any | None = None
        self.model_name = model_name
        self.max_entities = max_entities
        if not time_axis_past_words:
            msg = "time_axis_past_words must not be empty"
            raise ValueError(msg)
        if not time_axis_future_words:
            msg = "time_axis_future_words must not be empty"
            raise ValueError(msg)

        self.time_axis_past_words = time_axis_past_words
        self.time_axis_future_words = time_axis_future_words
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

    def _detect_time_axis(self, content_lower: str) -> str:
        """Detects the time axis of the text using configured temporal keywords."""
        if any(word in content_lower for word in self.time_axis_past_words):
            return "Past"
        if any(word in content_lower for word in self.time_axis_future_words):
            return "Future"
        return "Present"

    def _validate_and_sanitize(self, content: str) -> str:
        """Isolates the validation logic to keep complexity low."""

        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", content):
            msg = "Content contains forbidden control characters."
            raise ValueError(msg)

        # Use strict HTML/script sanitization with Bleach instead of brittle regex whitelists
        # that break on multi-language content and allow logic injections.
        sanitized = bleach.clean(content, tags=[], attributes={}, protocols=[], strip=True)

        # Enforce basic constraints
        if len(sanitized) > self.max_content_length:
            msg = "Content exceeds maximum length."
            raise ValueError(msg)

        return sanitized

    def tag_entities_and_axes(self, chunks: list[SemanticChunk]) -> None:
        """
        Public method to tag entities and multi-dimensional axes.
        """
        if self.nlp is None:
            msg = "NLP model is not loaded."
            raise RuntimeError(msg)

        for chunk in chunks:
            sanitized_content = self._validate_and_sanitize(chunk.content)

            if not sanitized_content.strip():
                continue

            doc = self.nlp(sanitized_content)
            extracted_entities = []
            allowed_types = {"PERSON", "ORG", "GPE", "PRODUCT"}

            ent_iter = iter(ent for ent in doc.ents if ent.label_ in allowed_types)
            collected = 0
            iterations = 0
            max_iterations = 1000

            while collected < self.max_entities:
                iterations += 1
                if iterations > max_iterations:
                    break
                batch = []
                try:
                    for _ in range(100):
                        batch.append(next(ent_iter).text)
                except StopIteration:
                    extracted_entities.extend(batch)
                    break

                extracted_entities.extend(batch)
                collected += len(batch)

            chunk.metadata.extracted_entities = list(set(extracted_entities[: self.max_entities]))
            chunk.metadata.time_axis = self._detect_time_axis(sanitized_content.lower())


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
        if len(user_answer) > 10000:
            msg = "Answer too long"
            raise ValueError(msg)
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


class PivotKJEngine(PivotEngineProtocol):
    """
    Engine to orchestrate dynamic re-clustering (Pivot KJ) of semantic chunks based
    on specific multi-dimensional axes (e.g., actor, timeline).
    """

    def __init__(self, allowed_axes: frozenset[str]) -> None:
        self._allowed_axes = allowed_axes

    def pivot(self, chunks: list[SemanticChunk], axis: str) -> dict[str, list[SemanticChunk]]:
        if not axis.isidentifier():
            msg = "Axis must be a valid identifier"
            raise ValueError(msg)
        """
        Dynamically relocates and clusters chunks based on explicitly defined metadata tags.
        """
        if not chunks:
            return {}

        axis_lower = axis.lower()
        if axis_lower not in self._allowed_axes:
            msg = f"Invalid axis '{axis}'. Supported axes are {', '.join(sorted(self._allowed_axes))}."
            logger.exception(msg)
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


class IngestionPipeline:
    """
    Orchestrates the document ingestion process: parsing, chunking, embedding,
    entity extraction, and mapping to the domain model format.
    """

    def __init__(
        self,
        llm: LLMProtocol,
        embedding: EmbeddingProtocol,
        text_parser: TextParserProtocol,
        max_sentences_per_chunk: int = 5,
    ) -> None:
        self._llm = llm
        self._embedding = embedding
        self._text_parser = text_parser
        self._max_sentences_per_chunk = max_sentences_per_chunk

        from src.config.settings import AppConfig

        self._config = AppConfig()

        from src.infrastructure.clustering import UMAPGMMClusteringStrategy

        self._raptor_engine = RaptorEngine(
            llm=llm,
            clustering_strategy=UMAPGMMClusteringStrategy(),
            max_clusters=self._config.raptor_max_clusters,
            max_content_length=self._config.max_content_length,
        )
        try:
            import spacy

            # Use the lightweight model for robust sentence splitting in the pipeline
            self._nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            self._nlp = None  # type: ignore[assignment]
            logger.warning(
                "Spacy model 'en_core_web_sm' not found. Falling back to simple chunking."
            )

    async def _extract_entities_and_tags(self, text: str) -> dict[str, Any]:
        """Calls the LLM to extract metadata tags (entities, time axis)."""
        prompt = _LLM_JSON_FORMAT_PROMPT.format(text=text)
        try:
            # We assume a text_fast_model for these metadata extractions
            from src.domain_models.config import ModelRoutingRules

            # Fallback for settings configuration mismatches
            model_name = getattr(self._config, "routing_rules", ModelRoutingRules()).text_fast_model
            response_text = await self._llm.generate_text(prompt, model=model_name)
            # Parse the JSON string
            # LLMs sometimes wrap json in markdown block
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(response_text)

            entities = data.get("entities", [])
            time_axis = data.get("time_axis", "Present")
            if not isinstance(entities, list):
                entities = []

            return {"entities": [str(e) for e in entities], "time_axis": str(time_axis)}
        except Exception as e:
            logger.warning(f"Failed to extract metadata from chunk: {e}")
            return {"entities": [], "time_axis": None}

    def _chunk_text(self, text: str) -> list[str]:
        """Chunks text semantically if spacy is available, else naively."""
        if not text:
            return []

        if self._nlp:
            doc = self._nlp(text)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            # A basic semantic chunker: group up to max_sentences_per_chunk sentences together to maintain some context
            chunks = []
            current_chunk = []
            for i, sent in enumerate(sentences):
                current_chunk.append(sent)
                if len(current_chunk) >= self._max_sentences_per_chunk or i == len(sentences) - 1:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
            return chunks
        # Fallback simple logic
        return [c.strip() for c in re.split(r"(?<=[.!?])\s+", text) if c.strip()]

    async def _process_single_chunk(self, text: str, filename: str) -> SemanticChunk:
        """Processes a single text chunk: embedding, metadata extraction, validation."""
        embed_task = self._embedding.embed_text(text)
        metadata_task = self._extract_entities_and_tags(text)

        embedding_vector, metadata_dict = await asyncio.gather(embed_task, metadata_task)

        metadata = ChunkMetadata(
            source_file=filename,
            extracted_entities=metadata_dict["entities"],
            time_axis=metadata_dict["time_axis"],
        )

        return SemanticChunk(
            id=uuid.uuid4(), content=text, embedding=embedding_vector, metadata=metadata
        )

    async def process_document(self, file_content: bytes, filename: str) -> list[SemanticChunk]:
        """
        Main pipeline to parse the document, chunk it, embed it, extract tags,
        and validate it all against the domain model rules.
        """
        parsed_text = await self._text_parser.parse(file_content, filename)

        raw_chunks = self._chunk_text(parsed_text)

        semantic_chunks = []
        # Process sequentially to not overwhelm limits in this cycle
        # although gather could be used, processing chunks requires care for rate limits.
        # But wait, FR-1.2 says concurrently (using asyncio.gather). I will use it for chunks.
        tasks = [self._process_single_chunk(text, filename) for text in raw_chunks]

        # We can gather them
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Chunk processing failed: {result}")
                # We can either fail the whole process or continue.
                # Let's fail if anything raises to maintain strict domain validation for UAT-03-03
                raise result
            semantic_chunks.append(result)

        # Additionally, validate that all chunk embeddings are consistent
        from src.domain_models.document import DocumentValidator

        DocumentValidator.validate_embedding_consistency(semantic_chunks)  # type: ignore[arg-type]

        return semantic_chunks  # type: ignore[return-value]

    async def build_enriched_document(self, file_content: bytes, filename: str) -> EnrichedDocument:
        """
        Processes the document into chunks and then builds the RAPTOR tree,
        returning the fully populated EnrichedDocument.
        """
        chunks = await self.process_document(file_content, filename)
        nodes = await self._raptor_engine.build_tree(chunks)

        from src.domain_models.document import DocumentFactory

        return DocumentFactory.create(
            document_id=uuid.uuid4(),
            original_text=filename,  # In a full flow, you might preserve original_text from text parser
            chunks=chunks,
            raptor_nodes=nodes,
        )


__all__ = [
    "IngestionPipeline",
    "NLPModelLoadError",
    "NLPService",
    "PivotKJEngine",
    "PivotWorkflow",
    "RaptorEngine",
    "SQ3REngine",
]
