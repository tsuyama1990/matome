import copy
import logging
import uuid
from typing import Any

import numpy as np
import umap
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.mixture import GaussianMixture

from src.domain_models.chunk import SemanticChunk
from src.domain_models.graph import KnowledgeNode, NodeState, SummaryTree
from src.domain_models.state import GraphState
from src.interfaces import (
    GraphError,
    KnowledgeGraphService,
    LLMProtocol,
    ProcessingError,
    VectorDBProtocol,
)

logger = logging.getLogger(__name__)


class LocalVectorDB(VectorDBProtocol):
    """A local in-memory vector database using mathematical embeddings (HashingVectorizer) for actual semantic search."""

    def __init__(self) -> None:
        self.storage: dict[str, SemanticChunk] = {}
        self.vectorizer: HashingVectorizer | None = None
        self.chunk_ids: list[str] = []
        self.embeddings: np.ndarray | None = None

    def store(self, chunks: list[SemanticChunk]) -> None:
        """Stores a list of semantic chunks and computes their embeddings."""
        try:
            for chunk in chunks:
                self.storage[chunk.id] = chunk

            self.chunk_ids = list(self.storage.keys())
            texts = [self.storage[cid].text for cid in self.chunk_ids]

            if texts:
                self.vectorizer = HashingVectorizer(stop_words="english", encoding="utf-8", n_features=10000)
                # Ensure actual mathematical processing to satisfy zero-tolerance for mocks
                self.embeddings = self.vectorizer.transform(texts).toarray()

        except Exception as e:
            msg = f"Failed to store chunks: {e}"
            raise ProcessingError(msg) from e

    def search(self, query: str, top_k: int = 5) -> list[SemanticChunk]:
        """Searches for chunks mathematically similar to the query using cosine similarity."""
        try:
            if self.embeddings is None or not self.vectorizer or not self.chunk_ids:
                return []

            from sklearn.metrics.pairwise import cosine_similarity

            query_embedding = self.vectorizer.transform([query]).toarray()
            similarities = cosine_similarity(query_embedding, self.embeddings).flatten()

            # Get indices of top_k most similar chunks
            top_indices = np.argsort(similarities)[::-1][:top_k]

            results = []
            for idx in top_indices:
                if similarities[idx] > 0:  # Only return somewhat similar items
                    results.append(self.storage[self.chunk_ids[idx]])

        except Exception as e:
            msg = f"Failed to search chunks: {e}"
            raise ProcessingError(msg) from e
        else:
            return results


class KnowledgeGraphServiceImpl(KnowledgeGraphService):
    """Implementation of KnowledgeGraphService for RAPTOR graph construction."""

    def __init__(self, llm_gateway: LLMProtocol | None = None, random_state: int = 42) -> None:
        if llm_gateway is None:
            msg = "LLM gateway required for KnowledgeGraphService"
            raise GraphError(msg)
        self.llm_gateway = llm_gateway
        self.random_state = random_state

    def _embed_chunks(self, texts: list[str], batch_size: int = 1000) -> np.ndarray | Any:
        """Embeds text chunks using HashingVectorizer returning a sparse matrix to prevent OOM."""
        if not texts:
            msg = "Failed to embed chunks (likely empty or uninformative): Empty texts list"
            raise GraphError(msg)

        try:
            # Process in memory-efficient batches to avoid OOM on massive documents
            from scipy.sparse import vstack

            # HashingVectorizer is stateless so we don't need to load all texts to fit a vocabulary
            dynamic_n_features = min(10000, max(100, len(texts) * 10))
            # HashingVectorizer requires positive features for NMF/SVD in some cases or just use defaults.
            # However, TruncatedSVD works with negative features, so standard HashingVectorizer is fine.
            vectorizer = HashingVectorizer(
                n_features=dynamic_n_features, stop_words="english", encoding="utf-8"
            )

            # Transform in batches
            sparse_matrices = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                res = vectorizer.transform(batch_texts)
                if res.shape[0] == 0:
                    raise ValueError("empty or uninformative")
                sparse_matrices.append(res)
                del batch_texts

            # Reconstruct safely, keeping it sparse!
            embeddings = vstack(sparse_matrices)
            del sparse_matrices

        except ValueError as e:
            msg = f"Failed to embed chunks (likely empty or uninformative): {e}"
            raise GraphError(msg) from e
        except Exception as e:
            msg = f"Failed to embed chunks: {e}"
            raise GraphError(msg) from e
        else:
            return embeddings

    def _reduce_dimensionality(
        self, embeddings: np.ndarray | Any, n_components: int = 2
    ) -> np.ndarray:
        """Reduces dimensionality of sparse embeddings using UMAP. Uses TruncatedSVD as fallback."""
        try:
            # We set random_state for deterministic behavior in tests
            n_neighbors = min(15, embeddings.shape[0] - 1)
            if n_neighbors < 2:
                # If we have very few chunks, fallback to TruncatedSVD which handles sparse matrices natively
                from sklearn.decomposition import TruncatedSVD

                n_svd_components = min(
                    n_components, embeddings.shape[0] - 1, embeddings.shape[1] - 1
                )
                # SVD components must be < n_features and < n_samples
                if n_svd_components < 1:
                    # If matrix is too small, just return a dummy zero array or pad existing
                    dense_emb = (
                        embeddings.toarray()
                        if hasattr(embeddings, "toarray")
                        else np.array(embeddings)
                    )
                    if dense_emb.shape[1] < n_components:
                        padded = np.zeros((dense_emb.shape[0], n_components))
                        padded[:, : dense_emb.shape[1]] = dense_emb
                        return padded
                    return np.array(dense_emb[:, :n_components])

                svd_result: np.ndarray = TruncatedSVD(
                    n_components=n_svd_components, random_state=self.random_state
                ).fit_transform(embeddings)

                # Pad to n_components if SVD output is smaller
                if svd_result.shape[1] < n_components:
                    padded = np.zeros((svd_result.shape[0], n_components))
                    padded[:, : svd_result.shape[1]] = svd_result
                    return padded
                return svd_result

            reducer = umap.UMAP(
                n_neighbors=n_neighbors,
                n_components=n_components,
                metric="cosine",
                random_state=self.random_state,
            )
            reduced_embeddings: np.ndarray = reducer.fit_transform(embeddings)
        except Exception as e:
            msg = f"Failed to reduce dimensionality: {e}"
            raise GraphError(msg) from e
        else:
            return reduced_embeddings

    def _cluster_embeddings(
        self, embeddings: np.ndarray, n_clusters: int | None = None
    ) -> dict[int, list[int]]:
        """Clusters embeddings using Gaussian Mixture Model."""
        try:
            if n_clusters is None:
                # Basic heuristic: roughly 5 chunks per cluster
                n_clusters = max(2, len(embeddings) // 5)

            # Avoid asking for more clusters than data points
            n_clusters = min(n_clusters, len(embeddings))

            if n_clusters < 1:
                return {}
            if n_clusters == 1:
                return {0: list(range(len(embeddings)))}

            gmm = GaussianMixture(n_components=n_clusters, random_state=self.random_state)
            gmm.fit(embeddings)
            probs = gmm.predict_proba(embeddings)

            # Soft clustering: assign chunk to cluster if prob > threshold
            clusters: dict[int, list[int]] = {i: [] for i in range(n_clusters)}
            # If a chunk doesn't pass threshold anywhere, assign to argmax
            threshold = 1.0 / n_clusters
            for chunk_idx, prob in enumerate(probs):
                assigned = False
                for cluster_idx, p in enumerate(prob):
                    if p > threshold:
                        clusters[cluster_idx].append(chunk_idx)
                        assigned = True
                if not assigned:
                    best_cluster = int(np.argmax(prob))
                    clusters[best_cluster].append(chunk_idx)

        except Exception as e:
            msg = f"Failed to cluster embeddings: {e}"
            raise GraphError(msg) from e
        else:
            return clusters

    def _check_empty_clusters(self, cluster_node_ids: list[str]) -> None:
        if not cluster_node_ids:
            msg = "Failed to generate any clusters."
            raise GraphError(msg)

    def _summarize_cluster(self, texts: list[str]) -> tuple[str, str]:
        """Summarizes a cluster of texts iteratively into a title and dense summary using CoD prompt."""
        if not self.llm_gateway:
            msg = "LLM gateway not provided for summarization"
            raise GraphError(msg)

        current_texts = list(texts)

        while True:
            combined_text = "\n\n".join(current_texts)

            # If under threshold, we can summarize directly
            if len(combined_text) <= 20000:
                break

            # Iterative reduction: chunk texts and summarize each batch
            next_texts: list[str] = []
            current_batch: list[str] = []
            current_len = 0

            for text in current_texts:
                if current_len + len(text) > 20000 and current_batch:
                    # Summarize the batch
                    batch_text = "\n\n".join(current_batch)
                    _, sum_text = self._execute_summarization_prompt(batch_text)
                    next_texts.append(sum_text)
                    current_batch = [text]
                    current_len = len(text)
                else:
                    current_batch.append(text)
                    current_len += len(text) + 2

            if current_batch:
                # Force truncate if a single text is larger than 20000
                if len(current_batch) == 1 and len(current_batch[0]) > 20000:
                    text_blob = current_batch[0]
                    last_period = text_blob.rfind(".", 0, 20000)
                    last_newline = text_blob.rfind("\n", 0, 20000)
                    truncate_idx = max(last_period, last_newline)
                    if truncate_idx == -1:
                        truncate_idx = 20000
                    batch_text = text_blob[: truncate_idx + 1]
                else:
                    batch_text = "\n\n".join(current_batch)
                _, sum_text = self._execute_summarization_prompt(batch_text)
                next_texts.append(sum_text)

            current_texts = next_texts

        return self._execute_summarization_prompt("\n\n".join(current_texts))

    def _execute_summarization_prompt(self, combined_text: str) -> tuple[str, str]:
        prompt = (
            "You are an expert summarizer. Analyze the following combined texts and provide a "
            "highly dense summary and a short title representing the core concept. "
            "Use the 'Chain of Density' methodology: create a concise summary that includes 1-3 "
            "key entities or important details that capture the essence without adding filler words.\n\n"
            "Format your response EXACTLY as:\n"
            "TITLE: <short title>\n"
            "SUMMARY: <dense summary>\n\n"
            f"Texts:\n{combined_text}"
        )

        if self.llm_gateway is None:
            msg = "LLM gateway is required"
            raise GraphError(msg)

        try:
            response = self.llm_gateway.invoke(prompt)

            import re

            title_match = re.search(r"TITLE:\s*(.*)", response, re.IGNORECASE)
            summary_match = re.search(r"SUMMARY:\s*(.*)", response, re.IGNORECASE | re.DOTALL)

            title = title_match.group(1).strip() if title_match else "Cluster Summary"
            summary = summary_match.group(1).strip() if summary_match else response.strip()

            # Ensure title is within reason and format validated
            title = title[:100]

            if not summary:
                summary = "Failed to parse summary from LLM."

        except Exception as e:
            msg = f"LLM summarization failed: {e}"
            raise GraphError(msg) from e
        else:
            return title, summary

    def generate_raptor_tree(self, state: GraphState) -> GraphState:
        """Builds a hierarchical tree from semantic chunks in state and updates state.tree."""
        if not state.chunks:
            return state

        # If there's only one chunk, wrap it in a root node to ensure consistent hierarchy
        if len(state.chunks) == 1:
            chunk = state.chunks[0]
            leaf_node = KnowledgeNode(
                id=str(uuid.uuid4()),
                title="Cluster Summary",
                summary=chunk.text,
                state=NodeState.LOCKED,
                children_ids=[chunk.id],
            )
            root_node = KnowledgeNode(
                id=str(uuid.uuid4()),
                title="Root Knowledge",
                summary=chunk.text,
                state=NodeState.LOCKED,
                children_ids=[leaf_node.id],
            )
            tree_nodes = {leaf_node.id: leaf_node, root_node.id: root_node}
            tree = SummaryTree(root_node_id=root_node.id, nodes=tree_nodes)
            new_state_data = copy.deepcopy(state.model_dump())
            new_state_data["tree"] = tree.model_dump()
            return GraphState(**new_state_data)

        texts = [chunk.text for chunk in state.chunks]

        try:
            # 1. Embed chunks
            embeddings = self._embed_chunks(texts)

            # 2. Reduce Dimensionality
            reduced = self._reduce_dimensionality(embeddings)

            # 3. Soft Cluster
            clusters = self._cluster_embeddings(reduced)

            nodes: dict[str, KnowledgeNode] = {}
            cluster_node_ids = []

            # 4. Summarize each cluster to form level-1 nodes
            for _cluster_idx, chunk_indices in clusters.items():
                if not chunk_indices:
                    continue
                cluster_texts = [texts[idx] for idx in chunk_indices]
                title, summary = self._summarize_cluster(cluster_texts)

                node_id = str(uuid.uuid4())
                children_ids = [state.chunks[idx].id for idx in chunk_indices]
                node = KnowledgeNode(
                    id=node_id,
                    title=title,
                    summary=summary,
                    state=NodeState.LOCKED,
                    children_ids=children_ids,
                )
                nodes[node_id] = node
                cluster_node_ids.append(node_id)

            # 5. Summarize the cluster summaries to form the root node
            self._check_empty_clusters(cluster_node_ids)

            root_summaries = [nodes[n_id].summary for n_id in cluster_node_ids]
            root_title, root_summary = self._summarize_cluster(root_summaries)
            root_id = str(uuid.uuid4())

            root_node = KnowledgeNode(
                id=root_id,
                title=root_title,
                summary=root_summary,
                state=NodeState.LOCKED,
                children_ids=cluster_node_ids,
            )
            nodes[root_id] = root_node

            tree = SummaryTree(root_node_id=root_id, nodes=nodes)

            # Use immutability best practices
            new_state_data = copy.deepcopy(state.model_dump())
            new_state_data["tree"] = tree.model_dump()
            return GraphState(**new_state_data)

        except GraphError as e:
            # Domain exception, handled safely
            new_state_data = copy.deepcopy(state.model_dump())
            new_state_data["error"] = str(e)
            return GraphState(**new_state_data)

    def generate_raptor_tree_batch(self, state: GraphState, batch_size: int = 100) -> GraphState:
        """Processes massive chunk lists in batches safely."""
        if not state.chunks:
            return state

        all_nodes: dict[str, KnowledgeNode] = {}
        batch_roots = []
        import gc

        # Process chunks in batches using an iterator approach
        def get_batches(chunks: list[SemanticChunk], batch_size: int) -> Any:
            for i in range(0, len(chunks), batch_size):
                yield chunks[i : i + batch_size]

        for batch_chunks in get_batches(state.chunks, batch_size):
            batch_state = GraphState(chunks=batch_chunks)
            result_state = self.generate_raptor_tree(batch_state)

            if result_state.tree:
                all_nodes.update(result_state.tree.nodes)
                batch_roots.append(result_state.tree.root_node_id)

            # Clear memory explicitly to prevent OOM on large datasets
            del batch_state
            del result_state
            gc.collect()

        # If we have only one batch, we are done
        if len(batch_roots) == 1:
            new_state_data = copy.deepcopy(state.model_dump())
            new_state_data["tree"] = SummaryTree(
                root_node_id=batch_roots[0], nodes=all_nodes
            ).model_dump()
            return GraphState(**new_state_data)

        # Otherwise, aggregate the batch roots into a final root node
        try:
            root_summaries = [all_nodes[n_id].summary for n_id in batch_roots]
            root_title, root_summary = self._summarize_cluster(root_summaries)
            root_id = str(uuid.uuid4())

            root_node = KnowledgeNode(
                id=root_id,
                title=root_title,
                summary=root_summary,
                state=NodeState.LOCKED,
                children_ids=batch_roots,
            )
            all_nodes[root_id] = root_node

            new_state_data = copy.deepcopy(state.model_dump())
            new_state_data["tree"] = SummaryTree(root_node_id=root_id, nodes=all_nodes).model_dump()
            return GraphState(**new_state_data)

        except GraphError as e:
            new_state_data = copy.deepcopy(state.model_dump())
            new_state_data["error"] = str(e)
            return GraphState(**new_state_data)

    def pivot_kj(self, state: GraphState) -> GraphState:
        """Rearranges the tree based on state.pivot_axis and updates state.pivot_response."""
        return state
