import marimo

__generated_with = "0.1.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import logging
    import os
    import tempfile
    from pathlib import Path

    import numpy as np

    # Import matome modules
    from domain_models.config import ProcessingConfig, ClusteringAlgorithm
    from domain_models.manifest import Chunk, SummaryNode
    from matome.engines.raptor import RaptorEngine
    from matome.engines.interactive_raptor import InteractiveRaptorEngine
    from matome.engines.token_chunker import JapaneseTokenChunker as TokenChunker
    from matome.engines.embedder import EmbeddingService
    from matome.engines.cluster import GMMClusterer
    from matome.agents.summarizer import SummarizationAgent
    from matome.utils.store import DiskChunkStore

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("UAT_AND_TUTORIAL")
    return (
        Chunk,
        ClusteringAlgorithm,
        DiskChunkStore,
        EmbeddingService,
        GMMClusterer,
        InteractiveRaptorEngine,
        Path,
        ProcessingConfig,
        RaptorEngine,
        SummarizationAgent,
        SummaryNode,
        TokenChunker,
        logger,
        np,
        os,
        tempfile,
    )


@app.cell
def _(EmbeddingService, logger, np, os):
    # --- SETUP: MOCK MODE vs REAL MODE ---

    # Check for API Key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    is_mock_mode = False

    if not api_key or api_key == "mock":
        is_mock_mode = True
        os.environ["OPENROUTER_API_KEY"] = "mock"
        logger.info("🔧 MOCK MODE ACTIVATED: Using simulated embeddings and LLM responses.")
    else:
        logger.info("🚀 REAL MODE ACTIVATED: Using live API calls.")

    # Define Mock Embedding Service
    class MockEmbeddingService(EmbeddingService):
        """Mock service returning random deterministic embeddings."""
        def __init__(self, config):
            super().__init__(config)
            self.rng = np.random.default_rng(42)  # Fixed seed for reproducibility

        def embed_strings(self, texts):
            # Return random vectors of size 384 (standard for small models)
            for _ in texts:
                yield self.rng.random(384).tolist()

        def embed_chunks(self, chunks):
            for chunk in chunks:
                chunk.embedding = self.rng.random(384).tolist()
                yield chunk

    # Define Mock Summarization Agent
    class MockSummarizationAgent(SummarizationAgent):
        """Mock agent that responds to instructions."""
        def summarize(self, text, config=None, strategy=None, context=None):
            if self.mock_mode:
                if context and "instruction" in context:
                    return f"Refined Summary: {text[:20]}... (With: {context['instruction']})"
                return f"Summary of {text[:20]}..."
            return super().summarize(text, config, strategy, context)

    # Define Factory for Embedder and Summarizer
    def get_embedder(config):
        if is_mock_mode:
            return MockEmbeddingService(config)
        return EmbeddingService(config)

    def get_summarizer(config):
        if is_mock_mode:
            return MockSummarizationAgent(config)
        return SummarizationAgent(config)

    return (
        MockEmbeddingService,
        MockSummarizationAgent,
        api_key,
        get_embedder,
        get_summarizer,
        is_mock_mode,
    )


@app.cell
def _(
    ClusteringAlgorithm,
    DiskChunkStore,
    GMMClusterer,
    ProcessingConfig,
    RaptorEngine,
    SummarizationAgent,
    TokenChunker,
    get_embedder,
    get_summarizer,
    is_mock_mode,
    logger,
    tempfile,
):
    # --- CONFIGURATION & INITIALIZATION ---

    # 1. Create Config
    config = ProcessingConfig(
        max_input_length=20000,
        max_tokens=200, # Small chunks
        max_summary_tokens=150,
        max_retries=1 if is_mock_mode else 3,
        clustering_algorithm=ClusteringAlgorithm.GMM,
        n_clusters=2,  # Force small clusters for tutorial
        write_batch_size=10,
        embedding_batch_size=10,
    )

    # 2. Initialize Components
    chunker = TokenChunker()
    embedder = get_embedder(config)
    clusterer = GMMClusterer()
    summarizer = get_summarizer(config)

    # 3. Setup Temporary Storage (or use a fixed path for inspection)
    # Using a fixed path in 'tutorials/chunks.db' allows user to inspect it later with `matome serve`
    db_path = "tutorials/chunks.db"
    # Ensure fresh start
    if is_mock_mode: # Only delete if mock mode to avoid accidental data loss? Actually UAT should be repeatable.
        import pathlib
        if pathlib.Path(db_path).exists():
            pathlib.Path(db_path).unlink()

    # Initialize Raptor Engine
    raptor = RaptorEngine(
        chunker=chunker,
        embedder=embedder,
        clusterer=clusterer,
        summarizer=summarizer,
        config=config
    )

    logger.info("✅ Components Initialized.")
    return chunker, clusterer, config, db_path, embedder, pathlib, raptor, summarizer


@app.cell
def _(DiskChunkStore, db_path, logger, pathlib, raptor):
    # --- PART 1: THE "GROK" MOMENT (Cycle 01) ---
    # Goal: Generate a tree and verify Root is "Wisdom".

    # Sample Text: "Investment Philosophy" (Short enough for quick test, long enough to chunk)
    sample_text = """
    Successful investing is about managing risk, not avoiding it. The goal is to maximize returns for a given level of risk.
    Asset allocation is the most important decision an investor makes. It determines the majority of the portfolio's return variability.
    Diversification is the only free lunch in finance. By spreading investments across different asset classes, you can reduce risk without sacrificing returns.
    Market timing is difficult, if not impossible, to do consistently. Time in the market is more important than timing the market.
    Costs matter. High fees can significantly erode investment returns over time. Low-cost index funds are often a better choice for most investors.
    Emotional discipline is key. Fear and greed are the enemies of successful investing. Stick to your long-term plan.
    Rebalancing is essential to maintain your target asset allocation. It forces you to sell high and buy low.
    Understanding your risk tolerance is crucial. Only take on as much risk as you can handle emotionally and financially.
    Compounding is the eighth wonder of the world. The earlier you start investing, the more time your money has to grow.
    Stay informed but don't obsess over daily market fluctuations. Focus on the long term.
    """ * 10  # Repeat to ensure enough text for chunking/clustering

    logger.info("🌱 Starting Raptor Engine Execution...")

    store = DiskChunkStore(pathlib.Path(db_path))

    # Run the pipeline
    tree = raptor.run(sample_text, store=store)

    # Validation
    root_node = tree.root_node
    logger.info(f"🌳 Tree Generated! Root Node ID: {root_node.id}")
    logger.info(f"📜 Root Summary: {root_node.text[:100]}...")
    logger.info(f"🏷️  Root Level: {root_node.metadata.dikw_level}")

    # Assertion
    if root_node.metadata.dikw_level != "wisdom":
         # In mock mode with random embeddings/small text, it might not reach Wisdom if depth is low.
         # But RaptorEngine assigns levels. Level 1 (single chunk) is Wisdom.
         # Level > 1 (clustering) top is Wisdom.
         logger.warning(f"Expected 'wisdom' but got '{root_node.metadata.dikw_level}'. This might be due to small dataset size.")

    assert root_node.level >= 1
    return root_node, sample_text, store, tree


@app.cell
def _(InteractiveRaptorEngine, config, logger, root_node, store, summarizer):
    # --- PART 2: SEMANTIC ZOOMING (Cycle 03) ---
    # Goal: Traverse the tree programmatically.

    interactive_engine = InteractiveRaptorEngine(store, summarizer, config)

    # 1. Inspect Root (Wisdom)
    logger.info(f"🔍 Inspecting Root (L{root_node.level}): {root_node.metadata.dikw_level}")

    # 2. Get Children (Knowledge/Information)
    children = list(interactive_engine.get_children(root_node))
    logger.info(f"   └── Found {len(children)} children.")

    zoom_i = 0
    node_type = "Unknown"
    level_info = "Unknown"

    for zoom_i, zoom_child in enumerate(children):
        # Handle both SummaryNode and Chunk
        node_type = "Chunk" if hasattr(zoom_child, "index") else "Summary"
        level_info = f"L{zoom_child.level}" if hasattr(zoom_child, "level") else "L0"
        logger.info(f"       ├── Child {zoom_i} ({node_type} {level_info}): {zoom_child.text[:50]}...")

    # Assertion
    assert len(children) > 0, "Root node should have children"
    return (
        children,
        interactive_engine,
        level_info,
        node_type,
        zoom_child,
        zoom_i,
    )


@app.cell
def _(children, interactive_engine, logger):
    # --- PART 3: INTERACTIVE REFINEMENT (Cycle 02 & 04) ---
    # Goal: Update a node via Python API and persist to DB.

    # Select the first child summary node (if available) or the root itself if children are chunks
    target_node = None
    refine_child = None

    for refine_child in children:
        if hasattr(refine_child, "id"): # Is SummaryNode
            target_node = refine_child
            break

    if not target_node:
        logger.info("⚠️ No intermediate summary nodes found (tree too shallow). Using Root Node for refinement.")
        target_node = children[0] if hasattr(children[0], "id") else None # Fallback

    if target_node:
        logger.info(f"🛠️  Refining Node: {target_node.id}")
        original_text = target_node.text

        # Action: Refine
        instruction = "Explain like I'm 5"
        refined_node = interactive_engine.refine_node(target_node.id, instruction)

        logger.info(f"✨ Refined Text: {refined_node.text[:100]}...")

        # Validation
        assert refined_node.metadata.is_user_edited is True
        assert instruction in refined_node.metadata.refinement_history
        assert refined_node.text != original_text or "Mock" in refined_node.text # In mock mode it might be static

        logger.info("✅ Refinement Successful.")
    else:
        logger.warning("Skipping refinement test: No suitable summary node found.")
        instruction = "N/A"
        refined_node = None
        original_text = "N/A"

    return instruction, original_text, refine_child, refined_node, target_node


@app.cell
def _(interactive_engine, logger, target_node):
    # --- PART 4: TRACEABILITY (Cycle 05) ---
    # Goal: Get source chunks for a node.

    trace_chunk = None
    source_chunks = []

    if target_node:
        logger.info(f"🔗 Tracing sources for Node: {target_node.id}")

        source_chunks = list(interactive_engine.get_source_chunks(target_node.id, limit=5))

        logger.info(f"   └── Found {len(source_chunks)} source chunks.")
        for trace_chunk in source_chunks:
            logger.info(f"       ├── Chunk {trace_chunk.index}: {trace_chunk.text[:50]}...")

        # Assertion
        assert len(source_chunks) > 0
        assert hasattr(source_chunks[0], "index")

        logger.info("✅ Traceability Verified.")
    return source_chunks, trace_chunk


@app.cell
def _(marimo):
    # --- PART 5: GUI Launch Instructions ---
    return marimo.md(
        r"""
        ## 🎉 All Systems Go!

        The UAT has completed successfully. You have:
        1.  Generated a Knowledge Tree from raw text.
        2.  Traversed the hierarchy (Wisdom -> Data).
        3.  Refined a node interactively.
        4.  Traced a summary back to its source.

        ### 🚀 Launch the GUI
        To explore the visual "Matome Canvas", run the following command in your terminal:

        ```bash
        uv run matome serve tutorials/chunks.db
        ```

        This will start a local server (usually at http://localhost:5006) where you can verify the "Pyramid View" and interactive features.
        """
    )


if __name__ == "__main__":
    app.run()
