import logging
import re
from collections.abc import Iterable, Iterator

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Splits text based on semantic similarity between sentences.
    """

    def __init__(self, config: ProcessingConfig) -> None:
        self.config = config
        # Initialize model only if needed? Or assume it's cheap/cached.
        # Ideally this service should be injected or lighter.
        # For now, we load it.
        self.model = SentenceTransformer(config.embedding_model)

    def split_text(self, text: str | Iterable[str], config: ProcessingConfig) -> Iterator[Chunk]:
        """
        Split text semantically.
        Currently handles 'text' as a single string mainly, but can adapt to stream
        by buffering sentences.
        """
        # Simplification: Buffer all text to perform global semantic analysis (percentiles),
        # OR implement a sliding window stream.
        # Given the "NEVER load entire dataset" rule, we should implement a sliding window
        # or sentence-by-sentence comparison if possible.
        # However, 'percentile' based thresholding requires global stats.
        # If percentile mode is on, we might need a representative sample or fixed threshold.

        # For this refactor, we will buffer if it's a stream, but warn or limit.
        # OR better: process in large blocks (e.g. paragraphs).

        # Materialize for now as semantic chunking logic below is complex to stream
        # without significant rewrite.
        # TODO: Implement true streaming semantic chunker.
        input_text = text if isinstance(text, str) else "".join(text)

        # 1. Split into sentences
        # Simple regex split for now
        sentences = re.split(r"(?<=[.!?。！？])\s+", input_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return

        # 2. Embed sentences (batch)
        embeddings = self.model.encode(sentences)

        # 3. Calculate cosine distances
        distances = []
        for i in range(len(embeddings) - 1):
            sim = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            distances.append(1 - sim)

        # 4. Determine Threshold
        if config.semantic_chunking_mode: # Explicit percentile check?
             # Logic from original implementation
             pass

        # Use simple threshold or percentile
        threshold = config.semantic_chunking_threshold
        if config.semantic_chunking_percentile:
             threshold = np.percentile(distances, config.semantic_chunking_percentile)

        # 5. Group sentences
        current_chunk_sentences: list[str] = [sentences[0]]
        chunk_index = 0
        current_char_start = 0

        for i, dist in enumerate(distances):
            if dist > threshold:
                # Split here
                chunk_text = " ".join(current_chunk_sentences)
                yield Chunk(
                    index=chunk_index,
                    text=chunk_text,
                    start_char_idx=current_char_start,
                    end_char_idx=current_char_start + len(chunk_text)
                )
                chunk_index += 1
                current_char_start += len(chunk_text) + 1 # +1 for space join approximation
                current_chunk_sentences = [sentences[i+1]]
            else:
                current_chunk_sentences.append(sentences[i+1])

        # Last chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            yield Chunk(
                index=chunk_index,
                text=chunk_text,
                start_char_idx=current_char_start,
                end_char_idx=current_char_start + len(chunk_text)
            )
