import marimo

__generated_with = "0.1.0"
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
    if str(Path.cwd()) not in sys.path:
        sys.path.append(str(Path.cwd()))

    # Matome Imports
    from domain_models.config import ProcessingConfig, ClusteringAlgorithm
    from domain_models.manifest import Chunk, SummaryNode
    from matome.engines.token_chunker import JapaneseTokenChunker
    from matome.engines.raptor import RaptorEngine
    from matome.utils.store import DiskChunkStore
    from matome.agents.summarizer import SummarizationAgent
    from matome.engines.cluster import GMMClusterer
    from matome.exporters.obsidian import ObsidianCanvasExporter
    from matome.engines.embedder import EmbeddingService

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("matome.tutorial")
    return (
        Any,
        Chunk,
        ClusteringAlgorithm,
        DiskChunkStore,
        EmbeddingService,
        GMMClusterer,
        Iterable,
        Iterator,
        JapaneseTokenChunker,
        ObsidianCanvasExporter,
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
def _(EmbeddingService, Iterable, Iterator, ProcessingConfig, logger, np):
    class MockEmbeddingService(EmbeddingService):
        """Mock Embedding Service that returns random vectors."""

        def __init__(self, config: ProcessingConfig) -> None:
            super().__init__(config)
            self.dim = 384  # Standard small model dimension

        def embed_strings(self, texts: Iterable[str]) -> Iterator[list[float]]:
            """Generate random embeddings for strings."""
            texts_list = list(texts)
            count = len(texts_list)
            logger.info(f"[Mock] Generating {count} random embeddings (dim={self.dim})")

            # Generate deterministic random vectors based on text length to avoid flux
            rng = np.random.default_rng(42)

            for _ in range(count):
                # Normalize to unit length like real embeddings
                vec = rng.standard_normal(self.dim)
                vec /= np.linalg.norm(vec)
                yield vec.tolist()

    return MockEmbeddingService,


@app.cell
def _(MockEmbeddingService, ProcessingConfig, os, Path):
    # --- Configuration & Mock Setup ---

    # Check for API Key
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    is_mock_mode = not api_key or api_key == "mock" or api_key == ""

    if is_mock_mode:
        print("⚠️  No API Key found. Running in **MOCK MODE**.")
        os.environ["OPENROUTER_API_KEY"] = "mock"
        # Use MockEmbeddingService
        EmbeddingServiceClass = MockEmbeddingService
    else:
        print("✅ API Key found. Running in **REAL MODE**.")
        from matome.engines.embedder import EmbeddingService as RealEmbeddingService
        EmbeddingServiceClass = RealEmbeddingService

    # Setup Config
    config = ProcessingConfig(
        summarization_model="openai/gpt-4o-mini",
        clustering_algorithm="gmm",
        max_tokens=100,  # Small chunks for tutorial
        max_summary_tokens=100,  # Ensure summary is not larger than chunk
        n_clusters=3, # Force small number of clusters
        write_batch_size=10,
        embedding_batch_size=10,
    )

    # Setup Paths
    TUTORIAL_DIR = Path("tutorials")
    TUTORIAL_DIR.mkdir(exist_ok=True)

    DB_PATH = TUTORIAL_DIR / "chunks.db"
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
            print(f"🧹 Cleaned up existing database: {DB_PATH}")
        except PermissionError:
            print(f"⚠️  Could not delete {DB_PATH}. Is it in use?")

    CANVAS_PATH = TUTORIAL_DIR / "summary_kj.canvas"

    return (
        CANVAS_PATH,
        DB_PATH,
        EmbeddingServiceClass,
        TUTORIAL_DIR,
        api_key,
        config,
        is_mock_mode,
    )


@app.cell
def _(JapaneseTokenChunker, config):
    # --- Part 1: Ingestion & Chunking ---

    # Sample Text (Excerpt about "Wisdom" vs "Data")
    SAMPLE_TEXT = """
    In the modern age, we are drowning in data but starving for wisdom.
    Data is raw facts, unorganized and unprocessed.
    Information is data that is processed to be useful.
    Knowledge is the application of data and information.
    Wisdom is the ability to think and act using knowledge, experience, understanding, common sense and insight.

    The Matome system is designed to traverse this hierarchy.
    It starts by breaking down text into small, manageable chunks.
    These chunks are then clustered based on semantic similarity.
    Each cluster is summarized to create a higher-level node.
    This process repeats recursively until a single root node - Wisdom - is formed.
    """ * 5  # Repeat to ensure we have enough text for multiple chunks

    print(f"📄 Loaded Sample Text ({len(SAMPLE_TEXT)} chars)")

    # Initialize Chunker
    chunker = JapaneseTokenChunker(config)

    # Chunk the text
    print("✂️  Chunking text...")
    initial_chunks = list(chunker.split_text(SAMPLE_TEXT, config))

    print(f"✅ Generated {len(initial_chunks)} chunks.")
    for i, chunk in enumerate(initial_chunks[:3]):
        print(f"   - Chunk {i}: {chunk.text[:50]}...")

    return SAMPLE_TEXT, chunker, initial_chunks


@app.cell
def _(
    DiskChunkStore,
    EmbeddingServiceClass,
    GMMClusterer,
    JapaneseTokenChunker,
    RaptorEngine,
    SummarizationAgent,
    config,
):
    # --- Part 2 & 3: Raptor Pipeline (Clustering & Summarization) ---

    print("\n🚀 Initializing Raptor Engine...")

    # Initialize Components
    embedder = EmbeddingServiceClass(config)
    clusterer = GMMClusterer() # No config in init
    summarizer = SummarizationAgent(config)
    chunker_instance = JapaneseTokenChunker(config)

    engine = RaptorEngine(
        chunker=chunker_instance,
        embedder=embedder,
        clusterer=clusterer,
        summarizer=summarizer,
        config=config
    )

    print("✅ Engine Initialized.")
    return clusterer, embedder, engine, summarizer


@app.cell
def _(DB_PATH, DiskChunkStore, SAMPLE_TEXT, engine):
    print(f"💾 Using Database: {DB_PATH}")

    # Use context manager for store
    with DiskChunkStore(DB_PATH) as store:
        print("▶️  Executing Pipeline (this may take a moment)...")
        # Run Raptor
        # Note: RaptorEngine.run() uses its own store context if store is None,
        # but here we pass an active store instance.
        tree = engine.run(SAMPLE_TEXT, store=store)

        print("\n✅ Pipeline Complete!")

        # Verify Root Node
        root = tree.root_node
        print(f"👑 Root Node ID: {root.id}")

        level = getattr(root, "level", "Unknown")
        dikw = "Unknown"
        if hasattr(root, "metadata") and root.metadata:
             dikw = root.metadata.dikw_level

        print(f"   Level: {level} ({dikw})")
        print(f"   Summary: {root.text[:100]}...")

    return dikw, level, root, tree


@app.cell
def _(
    CANVAS_PATH,
    DB_PATH,
    DiskChunkStore,
    ObsidianCanvasExporter,
    config,
    tree,
):
    # --- Part 4: Visualization & Export ---

    print(f"\n🎨 Exporting to Canvas: {CANVAS_PATH}")

    exporter = ObsidianCanvasExporter(config)

    # Re-open store to read nodes for export
    with DiskChunkStore(DB_PATH) as store_export:
        exporter.export(tree, CANVAS_PATH, store_export)

    print(f"✅ Exported to {CANVAS_PATH}")

    # Validation
    if CANVAS_PATH.exists():
        print("🎉 Verification Successful: Canvas file created.")
    else:
        print("❌ Verification Failed: Canvas file not found.")

    return exporter,


@app.cell
def _(DB_PATH):
    # --- Conclusion ---

    print("\n" + "="*50)
    print("🎉 All Systems Go: Matome 2.0 is ready for Knowledge Installation.")
    print("="*50)
    print("\nTo explore the results visually, run:")
    print(f"   uv run matome serve {DB_PATH}")
    print("\n" + "="*50)
    return


if __name__ == "__main__":
    app.run()
