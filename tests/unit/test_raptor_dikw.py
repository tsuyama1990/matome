from unittest.mock import MagicMock

import pytest

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, Cluster
from domain_models.types import DIKWLevel
from matome.agents.strategies import (
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)
from matome.engines.raptor import RaptorEngine
from matome.utils.store import DiskChunkStore


class MockStore(DiskChunkStore):
    def __init__(self):
        self.nodes = {}

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def add_chunks(self, chunks):
        for c in chunks:
            self.nodes[c.index] = c

    def add_summaries(self, summaries):
        for s in summaries:
            self.nodes[s.id] = s

    def update_node_embedding(self, node_id, embedding):
        if node_id in self.nodes:
            self.nodes[node_id].embedding = embedding

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture
def config_dikw():
    return ProcessingConfig(processing_mode="dikw", chunk_buffer_size=10)

def test_raptor_strategy_selection(config_dikw):
    chunker = MagicMock()
    embedder = MagicMock()
    clusterer = MagicMock()
    summarizer = MagicMock()

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config_dikw)

    # Mock behavior for _get_strategy_for_level
    # Level 1 -> Information
    strategy_l1 = engine._get_strategy_for_level(level=1, cluster_count=10)
    assert isinstance(strategy_l1, InformationStrategy)

    # Level 2 -> Knowledge (if count > 1)
    strategy_l2 = engine._get_strategy_for_level(level=2, cluster_count=5)
    assert isinstance(strategy_l2, KnowledgeStrategy)

    # Root -> Wisdom (count == 1)
    strategy_root = engine._get_strategy_for_level(level=3, cluster_count=1)
    assert isinstance(strategy_root, WisdomStrategy)

def test_raptor_summarize_clusters_dikw(config_dikw):
    chunker = MagicMock()
    embedder = MagicMock()
    clusterer = MagicMock()
    summarizer = MagicMock()
    summarizer.summarize.return_value = "Summary"

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config_dikw)
    store = MockStore()

    # Setup store with some chunks
    chunk = Chunk(index=0, text="Chunk Text", start_char_idx=0, end_char_idx=10)
    store.add_chunks([chunk])

    clusters = [Cluster(id=0, level=0, node_indices=[0])]
    current_level_ids = [0]

    # Call _summarize_clusters with InformationStrategy
    strategy = InformationStrategy()
    nodes = list(engine._summarize_clusters(clusters, current_level_ids, store, level=1, strategy=strategy))

    assert len(nodes) == 1
    node = nodes[0]
    assert node.metadata.dikw_level == DIKWLevel.INFORMATION
    assert node.metadata.cluster_id == 0

    # Verify summarizer called with strategy
    summarizer.summarize.assert_called_with("Chunk Text", config_dikw, strategy=strategy)
