import logging
import re
from typing import Any

from src.config import Settings
from src.domain_models.interfaces import (
    AIServiceError,
    ClusteringServiceProtocol,
    EntityExtractorProtocol,
    HTTPClientProtocol,
    RetryPolicyProtocol,
    TextSplitterProtocol,
)

logger = logging.getLogger(__name__)


class DefaultTextSplitter(TextSplitterProtocol):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    def split_text(self, text: str) -> list[str]:
        logger.debug("Executing LangChain semantic chunking...")
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
            )
            chunks = splitter.split_text(text)
        except ImportError:
            logger.warning("LangChain not installed, falling back to pure python overlap split.")
            step = self.chunk_size - self.chunk_overlap
            chunks = []
            for i in range(0, len(text), step):
                chunks.append(text[i : i + self.chunk_size])

        if not chunks:
            msg = "Semantic chunking returned no content."
            raise ValueError(msg)
        return chunks


class DefaultEntityExtractor(EntityExtractorProtocol):
    def extract_entities(self, chunks: list[str]) -> dict[str, str]:
        logger.debug("Executing SpaCy NER logic...")
        entities = {}
        try:
            import spacy

            nlp = spacy.load("en_core_web_sm")
            for i, chunk in enumerate(chunks):
                doc = nlp(chunk)
                for ent in doc.ents:
                    entities[f"chunk_{i}_{ent.label_}"] = ent.text
        except (ImportError, OSError) as e:
            logger.warning(
                f"SpaCy module/model not loaded: {e}. Falling back to regex entity extraction."
            )
            for i, chunk in enumerate(chunks):
                matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", chunk)
                if matches:
                    entities[f"chunk_{i}_Fallback_ORG"] = matches[0]
            if not entities:
                entities["document_level"] = "No obvious entities found"
        return entities


class DefaultClusteringService(ClusteringServiceProtocol):
    def cluster_chunks(self, chunks: list[str], max_clusters: int) -> dict[str, str]:
        if max_clusters < 1:
            msg = "max_clusters must be at least 1"
            raise ValueError(msg)

        logger.debug("Executing UMAP/GMM clustering for RAPTOR tree generation...")
        if len(chunks) < 3:
            return {"level_0": "root", "clusters_found": "1 (not enough chunks for clustering)"}

        try:
            import numpy as np
            import umap
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.mixture import GaussianMixture
        except ImportError as e:
            logger.warning(f"ML dependency missing: {e}. Returning basic flat tree.")
            return {
                "level_0": "root",
                "algorithm": "None (Missing ML modules)",
                "nodes": str(len(chunks)),
            }

        try:
            # Dummy embedding step (usually this is done with an LLM embedder)
            vectorizer = TfidfVectorizer()
            embeddings = vectorizer.fit_transform(chunks).toarray()

            # Reduce dimensionality
            n_neighbors = min(15, len(chunks) - 1)
            reducer = umap.UMAP(
                n_neighbors=n_neighbors, min_dist=0.1, metric="cosine", random_state=42
            )
            reduced_embeddings = reducer.fit_transform(embeddings)

            # Cluster
            n_components = min(max_clusters, len(chunks))
            gmm = GaussianMixture(n_components=n_components, random_state=42)
            clusters = gmm.fit_predict(reduced_embeddings)

            return {
                "level_0": "root",
                "clusters_found": str(len(np.unique(clusters))),
                "algorithm": "UMAP+GMM",
            }
        except Exception as e:
            logger.exception(
                "RAPTOR processing failed during mathematical execution. Falling back."
            )
            return {"level_0": "root", "error_fallback": str(e)}


class RequestsHTTPClient(HTTPClientProtocol):
    def post(
        self, url: str, json: dict[str, Any], headers: dict[str, str], timeout: int
    ) -> dict[str, Any]:
        import requests

        try:
            response = requests.post(url, json=json, headers=headers, timeout=timeout)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except requests.Timeout as e:
            msg = "The AI service request timed out."
            raise AIServiceError(msg) from e
        except requests.HTTPError as e:
            msg = f"The AI service returned an HTTP error: {e}"
            raise AIServiceError(msg) from e
        except requests.RequestException as e:
            msg = f"Failed to communicate with AI service: {e}"
            raise AIServiceError(msg) from e
        else:
            return data


class TenacityRetryPolicy(RetryPolicyProtocol):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self, func: Any) -> Any:
        from tenacity import Retrying, stop_after_attempt, wait_exponential_jitter

        retryer = Retrying(
            stop=stop_after_attempt(self.settings.ai_retry_attempts),
            wait=wait_exponential_jitter(
                initial=self.settings.ai_retry_min_wait, max=self.settings.ai_retry_max_wait
            ),
            reraise=True,
        )

        def _wrapper() -> Any:
            return func()

        return retryer(_wrapper)
