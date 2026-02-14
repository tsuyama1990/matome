from collections.abc import Iterator
from unittest.mock import MagicMock, create_autospec

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.cluster import GMMClusterer
from matome.engines.raptor import RaptorEngine
from matome.interfaces import Chunker, Summarizer


class UATEmbedder:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.config = MagicMock()

    def embed_chunks(self, chunks: Iterator[Chunk]) -> Iterator[Chunk]:
        # Process strictly as iterator
        for _i, c in enumerate(chunks):
            vec = [0.0] * self.dim
            # 5 groups of 10 chunks logic
            group_id = c.index // 10
            if group_id < self.dim:
                vec[group_id] = 1.0
            c.embedding = vec
            yield c

    def embed_strings(self, texts: list[str]) -> Iterator[list[float]]:
        for _ in texts:
            vec = [0.0] * self.dim
            vec[100] = 1.0
            yield vec


@pytest.fixture
def uat_config() -> ProcessingConfig:
    return ProcessingConfig(
        umap_n_neighbors=5,
        umap_min_dist=0.0,
    )


def test_uat_scenario_11_single_level(uat_config: ProcessingConfig) -> None:
    """
    Scenario 11: Single-Level Summarization (Priority: Medium)
    """
    chunker = create_autospec(Chunker, instance=True)

    def chunk_gen() -> Iterator[Chunk]:
        for i in range(3):
            yield Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=10)

    chunker.split_text.return_value = chunk_gen()

    embedder = UATEmbedder()
    clusterer = GMMClusterer()

    summarizer = create_autospec(Summarizer, instance=True)
    summarizer.summarize.return_value = "Summary Root"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, uat_config)  # type: ignore
    tree = engine.run("Short doc")

    assert tree.root_node.level == 1
    assert len(tree.leaf_chunk_ids) == 3
    assert tree.root_node.text == "Summary Root"


def test_uat_scenario_12_multi_level(uat_config: ProcessingConfig) -> None:
    """
    Scenario 12: Multi-Level Tree Construction (Priority: High)
    """
    chunker = create_autospec(Chunker, instance=True)

    def chunk_gen_large() -> Iterator[Chunk]:
        for i in range(50):
            yield Chunk(index=i, text=f"Chunk {i}", start_char_idx=0, end_char_idx=10)

    chunker.split_text.return_value = chunk_gen_large()

    embedder = UATEmbedder()
    clusterer = GMMClusterer()

    summarizer = create_autospec(Summarizer, instance=True)
    summarizer.summarize.return_value = "Summary Node"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, uat_config)  # type: ignore
    tree = engine.run("Long doc")

    assert tree.root_node.level >= 2
    assert len(tree.leaf_chunk_ids) == 50
    # Check that we have intermediate summaries via children indices logic or store
    # Since tree doesn't have all_nodes, we assume recursive process worked if level >= 2


def test_uat_scenario_13_summary_coherence() -> None:
    """
    Scenario 13: Summary Coherence Check (Priority: High)
    """
    config = ProcessingConfig(umap_n_neighbors=2, umap_min_dist=0.0)

    chunker = create_autospec(Chunker, instance=True)
    def chunk_gen_coherent() -> Iterator[Chunk]:
        yield Chunk(index=0, text="Climate change is real.", start_char_idx=0, end_char_idx=20)
        yield Chunk(index=1, text="Sea levels are rising.", start_char_idx=20, end_char_idx=40)

    chunker.split_text.return_value = chunk_gen_coherent()

    embedder = UATEmbedder()
    clusterer = GMMClusterer()

    summarizer = create_autospec(Summarizer, instance=True)
    summarizer.summarize.return_value = "Global Warming Summary"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)  # type: ignore
    tree = engine.run("Climate doc")

    assert tree.root_node.text == "Global Warming Summary"

    calls = summarizer.summarize.call_args_list
    assert len(calls) > 0
    args, _ = calls[0]
    input_text = args[0]
    assert "Climate change is real." in input_text
    assert "Sea levels are rising." in input_text
