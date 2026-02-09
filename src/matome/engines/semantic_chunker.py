import logging
from collections.abc import Iterator

import numpy as np

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService
from matome.utils.compat import batched
from matome.utils.text import iter_normalized_sentences

# Configure logger
logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(v1)
    b = np.array(v2)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class JapaneseSemanticChunker:
    """
    Chunking engine that splits text based on semantic similarity.

    1. Splits text into sentences using Japanese heuristics.
    2. Embeds sentences (streaming).
    3. Merges sentences into chunks if their similarity is high,
       respecting the max_tokens limit.
    """

    def __init__(self, embedder: EmbeddingService) -> None:
        """
        Initialize with an embedding service.

        Args:
            embedder: Service to generate embeddings for sentences.
        """
        self.embedder = embedder

    def split_text(self, text: str, config: ProcessingConfig) -> Iterator[Chunk]:
        """
        Split text into semantic chunks (streaming).

        This implementation streams sentences and embeddings to minimize memory usage,
        avoiding materialization of all sentence embeddings at once.

        Note: The returned chunks contain *normalized* text (NFKC), and the indices
        refer to positions in this normalized text.

        Args:
            text: Raw input text.
            config: Configuration including semantic_chunking_threshold and max_tokens.

        Yields:
            Chunk objects.

        Raises:
            ValueError: If input text is not a string.
        """
        self._validate_input(text)

        if not text:
            return

        # 1. Streaming Normalization & Processing
        # We iterate raw sentences and normalize them one by one.
        # This avoids creating a huge normalized string in memory.

        sentences_gen = iter_normalized_sentences(text)

        # State for chunk accumulation
        current_chunk_sentences: list[str] = []
        current_chunk_len = 0
        current_last_embedding: list[float] | None = None
        current_start_idx = 0
        current_chunk_index = 0

        try:
            # Iterate in batches of sentences (e.g. 32 at a time)
            # This aligns with embedding batch size for efficiency
            for sentence_batch_tuple in batched(sentences_gen, config.embedding_batch_size):
                sentence_batch = list(sentence_batch_tuple)

                # Embed this batch
                # embed_strings returns an iterator, we consume it immediately for this small batch
                embedding_batch = list(self.embedder.embed_strings(sentence_batch))

                if len(sentence_batch) != len(embedding_batch):
                    logger.warning(
                        f"Mismatch between sentences ({len(sentence_batch)}) and embeddings ({len(embedding_batch)})."
                    )
                    # Should ideally fail or handle gracefully.
                    # For now, zip will stop at shortest, but let's be safe.

                # Process this batch
                for sentence, embedding in zip(sentence_batch, embedding_batch, strict=False):
                    if current_last_embedding is None:
                        # First sentence of the very first chunk
                        current_chunk_sentences = [sentence]
                        current_chunk_len = len(sentence)
                        current_last_embedding = embedding
                        continue

                    # Logic for merging
                    similarity = cosine_similarity(current_last_embedding, embedding)
                    sentence_len = len(sentence)

                    if (similarity >= config.semantic_chunking_threshold) and (
                        current_chunk_len + sentence_len < config.max_tokens
                    ):
                        current_chunk_sentences.append(sentence)
                        current_chunk_len += sentence_len
                        current_last_embedding = embedding
                    else:
                        # Finalize current chunk
                        chunk_text = "".join(current_chunk_sentences)
                        yield Chunk(
                            index=current_chunk_index,
                            text=chunk_text,
                            start_char_idx=current_start_idx,
                            end_char_idx=current_start_idx + len(chunk_text),
                            embedding=None,
                        )
                        current_chunk_index += 1
                        current_start_idx += len(chunk_text)

                        # Start new chunk with current sentence
                        current_chunk_sentences = [sentence]
                        current_chunk_len = sentence_len
                        current_last_embedding = embedding

            # Final flush after all batches
            if current_chunk_sentences:
                chunk_text = "".join(current_chunk_sentences)
                yield Chunk(
                    index=current_chunk_index,
                    text=chunk_text,
                    start_char_idx=current_start_idx,
                    end_char_idx=current_start_idx + len(chunk_text),
                    embedding=None,
                )

        except Exception:
            logger.exception("Error during semantic chunking process.")
            raise

    def _validate_input(self, text: str) -> None:
        if not isinstance(text, str):
            msg = f"Input text must be a string, got {type(text)}."
            raise TypeError(msg)
