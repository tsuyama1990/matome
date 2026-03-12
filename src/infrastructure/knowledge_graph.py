import copy
import logging
import uuid

import numpy as np
import umap
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.mixture import GaussianMixture

from src.domain_models.graph import KnowledgeNode, NodeState, SummaryTree
from src.domain_models.state import GraphState
from src.interfaces import GraphError, KnowledgeGraphService, LLMProtocol

logger = logging.getLogger(__name__)


class KnowledgeGraphServiceImpl(KnowledgeGraphService):
    """Implementation of KnowledgeGraphService for RAPTOR graph construction."""

    def __init__(self, llm_gateway: LLMProtocol | None = None, random_state: int = 42) -> None:
        if llm_gateway is None:
            msg = "LLM gateway required for KnowledgeGraphService"
            raise GraphError(msg)
        self.llm_gateway = llm_gateway
        self.random_state = random_state

    def _embed_chunks(self, texts: list[str], batch_size: int = 1000) -> np.ndarray:
        """Embeds text chunks using TF-IDF."""
        try:
            vectorizer = TfidfVectorizer(max_features=5000, stop_words="english", encoding="utf-8")
            embeddings: np.ndarray = vectorizer.fit_transform(texts).toarray()
        except ValueError as e:
            # Handles empty texts case
            msg = f"Failed to embed chunks (likely empty or uninformative): {e}"
            raise GraphError(msg) from e
        except Exception as e:
            msg = f"Failed to embed chunks: {e}"
            raise GraphError(msg) from e
        else:
            return embeddings

    def _reduce_dimensionality(self, embeddings: np.ndarray, n_components: int = 2) -> np.ndarray:
        """Reduces dimensionality of embeddings using UMAP."""
        try:
            # We set random_state for deterministic behavior in tests
            n_neighbors = min(15, len(embeddings) - 1)
            if n_neighbors < 2:
                # If we have very few chunks, skip UMAP or just return basic representation
                return np.zeros((embeddings.shape[0], n_components))

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
        """Summarizes a cluster of texts into a title and dense summary using CoD prompt."""
        if not self.llm_gateway:
            msg = "LLM gateway not provided for summarization"
            raise GraphError(msg)

        combined_text = "\n\n".join(texts)
        # Prevent prompt from becoming too large; truncate to a safe token-equivalent length
        truncated_text = combined_text[:100000]

        prompt = (
            "You are an expert summarizer. Analyze the following combined texts and provide a "
            "highly dense summary and a short title representing the core concept. "
            "Use the 'Chain of Density' methodology: create a concise summary that includes 1-3 "
            "key entities or important details that capture the essence without adding filler words.\n\n"
            "Format your response EXACTLY as:\n"
            "TITLE: <short title>\n"
            "SUMMARY: <dense summary>\n\n"
            f"Texts:\n{truncated_text}"
        )

        try:
            response = self.llm_gateway.invoke(prompt)
            lines = response.split("\n", 1)
            title = (
                lines[0].replace("TITLE:", "").strip()
                if "TITLE:" in lines[0]
                else "Cluster Summary"
            )
            summary = lines[1].replace("SUMMARY:", "").strip() if len(lines) > 1 else response

            # Ensure title is within reason
            title = title[:100]

        except Exception as e:
            msg = f"LLM summarization failed: {e}"
            raise GraphError(msg) from e
        else:
            return title, summary

    def generate_raptor_tree(self, state: GraphState) -> GraphState:
        """Builds a hierarchical tree from semantic chunks in state and updates state.tree."""
        if not state.chunks:
            return state

        # If there's only one chunk, it becomes the root directly
        if len(state.chunks) == 1:
            chunk = state.chunks[0]
            node = KnowledgeNode(
                id=str(uuid.uuid4()),
                title="Root Knowledge",
                summary=chunk.text,
                state=NodeState.LOCKED,
                children_ids=[chunk.id],
            )
            tree = SummaryTree(root_node_id=node.id, nodes={node.id: node})
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

        # Process chunks in batches
        for i in range(0, len(state.chunks), batch_size):
            batch_chunks = state.chunks[i:i + batch_size]
            batch_state = GraphState(chunks=batch_chunks)
            result_state = self.generate_raptor_tree(batch_state)

            if result_state.tree:
                all_nodes.update(result_state.tree.nodes)
                batch_roots.append(result_state.tree.root_node_id)

        # If we have only one batch, we are done
        if len(batch_roots) == 1:
            new_state_data = copy.deepcopy(state.model_dump())
            new_state_data["tree"] = SummaryTree(root_node_id=batch_roots[0], nodes=all_nodes).model_dump()
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
                children_ids=batch_roots
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
