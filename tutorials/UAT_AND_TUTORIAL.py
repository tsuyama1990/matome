import marimo

__generated_with = "0.10.19"
app = marimo.App(width="medium")


@app.cell
def _():
    import logging
    import os
    import shutil
    import sys
    import uuid
    from collections.abc import Iterable, Iterator
    from pathlib import Path
    from typing import Any

    import numpy as np

    # Add src to path if running from root
    if "src" not in sys.path:
        sys.path.append("src")

    from domain_models.config import ProcessingConfig
    from domain_models.manifest import Chunk, SummaryNode
    from domain_models.types import DIKWLevel
    from matome.agents.summarizer import SummarizationAgent
    from matome.engines.cluster import GMMClusterer
    from matome.engines.embedder import EmbeddingService
    from matome.engines.interactive_raptor import InteractiveRaptorEngine
    from matome.engines.raptor import RaptorEngine
    from matome.engines.token_chunker import JapaneseTokenChunker
    from matome.utils.store import DiskChunkStore

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("matome.tutorial")
    return (
        Chunk,
        DIKWLevel,
        DiskChunkStore,
        EmbeddingService,
        GMMClusterer,
        InteractiveRaptorEngine,
        Iterable,
        Iterator,
        JapaneseTokenChunker,
        Path,
        ProcessingConfig,
        RaptorEngine,
        SummarizationAgent,
        SummaryNode,
        logger,
        logging,
        np,
        os,
        shutil,
        sys,
        uuid,
    )


@app.cell
def _(Iterable, Iterator, ProcessingConfig, logger, np):
    class MockEmbeddingService:
        """Mock embedding service that returns random vectors."""

        def __init__(self, config: ProcessingConfig) -> None:
            self.config = config
            # Use fixed seed for reproducibility in tests
            np.random.seed(42)

        def embed_strings(self, texts: Iterable[str]) -> Iterator[list[float]]:
            """Generate random embeddings for strings."""
            for _ in texts:
                # Generate random vector of size 384 (standard for small models)
                yield np.random.rand(384).tolist()

        def embed_chunks(self, chunks: Iterable[Any]) -> Iterator[Any]:
            """Generate random embeddings for chunks."""
            for chunk in chunks:
                chunk.embedding = np.random.rand(384).tolist()
                yield chunk

    logger.info("MockEmbeddingService defined.")
    return (MockEmbeddingService,)


@app.cell
def _(
    DiskChunkStore,
    EmbeddingService,
    JapaneseTokenChunker,
    MockEmbeddingService,
    ProcessingConfig,
    SummarizationAgent,
    logger,
    os,
    shutil,
):
    # Setup Configuration and Environment

    # 1. Setup DB Path
    db_path = "tutorials/chunks.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(f"{db_path}-shm"):
        os.remove(f"{db_path}-shm")
    if os.path.exists(f"{db_path}-wal"):
        os.remove(f"{db_path}-wal")

    # 2. Setup Config
    # Use 'mock' API key if not present to trigger mock mode in agents
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "mock"
        os.environ["OPENROUTER_API_KEY"] = "mock"
        logger.info("Running in MOCK MODE (No API Key found)")
    else:
        logger.info("Running in REAL MODE (API Key found)")

    config = ProcessingConfig(
        max_tokens=100,  # Small chunk size to force multiple chunks for small text
        max_summary_tokens=50,
        clustering_probability_threshold=0.1, # Low threshold to ensure clustering
        umap_n_neighbors=2, # Small number for small dataset
        umap_n_components=2,
        umap_min_dist=0.0,
    )

    # 3. Initialize Components
    store = DiskChunkStore(db_path=Path(db_path))
    chunker = JapaneseTokenChunker(config)

    if os.environ.get("OPENAI_API_KEY") == "mock":
        embedder = MockEmbeddingService(config)
    else:
        # Reuse imported EmbeddingService
        embedder = EmbeddingService(config)

    # Summarization Agent (Mock mode handled internally by checking API key)
    summarizer = SummarizationAgent(config)

    logger.info("Components initialized.")
    return (
        chunker,
        config,
        db_path,
        embedder,
        store,
        summarizer,
    )


@app.cell
def _(
    GMMClusterer,
    RaptorEngine,
    chunker,
    config,
    embedder,
    logger,
    store,
    summarizer,
):
    # Cycle 01: Wisdom Generation (Build the Tree)

    # Sample Text (Investment Philosophy style)
    sample_text = """
    長期投資の基本は、企業の成長と共に資産を増やすことです。
    短期的な市場の変動に惑わされず、本質的な価値を見極める必要があります。

    複利の効果は時間を味方につけることで最大化されます。
    雪だるま式に資産が増えるこの仕組みを理解することが重要です。

    リスク管理は分散投資によって行います。
    一つのカゴにすべての卵を盛るな、という格言の通りです。

    最後に、自己への投資も忘れてはいけません。
    知識こそが最大の防御であり、最大の武器となるのです。
    """

    logger.info("Starting Cycle 01: Wisdom Generation...")

    clusterer = GMMClusterer()

    # Initialize Raptor Engine
    engine = RaptorEngine(
        chunker=chunker,
        embedder=embedder,
        clusterer=clusterer,
        summarizer=summarizer,
        config=config
    )

    # Run Engine
    tree = engine.run(sample_text, store=store)

    logger.info(f"Tree generation complete. Root ID: {tree.root_node.id}")

    # Validation
    root_node = tree.root_node
    logger.info(f"Root Node DIKW Level: {root_node.metadata.dikw_level}")

    assert root_node is not None
    assert root_node.metadata.dikw_level.value in ["wisdom", "knowledge", "information"]

    logger.info("✅ Cycle 01 Passed: Tree built and Root Node verified.")
    return clusterer, engine, root_node, sample_text, tree


@app.cell
def _(DIKWLevel, logger, store, tree):
    # Cycle 03: Semantic Zooming (Traverse Tree)

    logger.info("Starting Cycle 03: Semantic Zooming...")

    # 1. Get Root (Wisdom)
    root = tree.root_node
    print(f"L1 (Root): {root.text[:50]}...")

    # 2. Get Children (Knowledge/Information)
    # Using store to fetch children
    child_ids = root.children_indices
    children = list(store.get_nodes(child_ids))

    logger.info(f"Found {len(children)} children for Root.")

    for child in children:
        if child:
            is_summary = hasattr(child, "metadata") and hasattr(child.metadata, "dikw_level")
            type_str = child.metadata.dikw_level.value if is_summary else "DATA (Chunk)"
            print(f"  - L2 ({type_str}): {child.text[:30]}...")

    # Validation
    assert len(children) > 0

    logger.info("✅ Cycle 03 Passed: Tree traversal verified.")
    return child, child_ids, children, is_summary, root, type_str


@app.cell
def _(InteractiveRaptorEngine, config, logger, root_node, store, summarizer):
    # Cycle 02/04: Interactive Refinement

    logger.info("Starting Cycle 02/04: Interactive Refinement...")

    interactive_engine = InteractiveRaptorEngine(
        store=store,
        summarizer=summarizer,
        config=config
    )

    # 1. Select a node to refine (Root node for simplicity)
    node_id = root_node.id
    instruction = "Make it more concise and focused on risk."

    logger.info(f"Refining node {node_id} with instruction: '{instruction}'")

    # 2. Call Refine
    updated_node = interactive_engine.refine_node(node_id, instruction)

    # 3. Validation
    assert updated_node.id == node_id
    assert updated_node.metadata.is_user_edited is True
    assert instruction in updated_node.metadata.refinement_history

    print(f"Original Text: {root_node.text[:50]}...")
    print(f"Refined Text:  {updated_node.text[:50]}...")

    # Check if text changed
    assert updated_node.text != root_node.text or "Summary of" in updated_node.text

    logger.info("✅ Cycle 02/04 Passed: Node refinement verified.")
    return (
        instruction,
        interactive_engine,
        node_id,
        updated_node,
    )


@app.cell
def _(interactive_engine, logger, node_id, sample_text):
    # Cycle 05: Traceability (Source Verification)

    logger.info("Starting Cycle 05: Traceability...")

    # 1. Get Source Chunks for the node
    source_chunks = list(interactive_engine.get_source_chunks(node_id))

    logger.info(f"Found {len(source_chunks)} source chunks.")

    # 2. Validation
    assert len(source_chunks) > 0

    first_chunk_text = source_chunks[0].text
    assert len(first_chunk_text) > 0

    print(f"Source Chunk 1: {first_chunk_text[:50]}...")

    logger.info("✅ Cycle 05 Passed: Source chunks retrieved.")
    return first_chunk_text, source_chunks


@app.cell
def _(logger):
    print("\n")
    logger.info("🎉 All Systems Go: Matome 2.0 is ready for Knowledge Installation.")
    return


if __name__ == "__main__":
    app.run()
