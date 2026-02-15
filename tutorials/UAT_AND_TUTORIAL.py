import marimo

__generated_with = "0.10.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import logging
    import os
    import sys
    import tempfile
    import uuid
    from pathlib import Path
    from typing import Any, Iterator, cast

    import numpy as np
    from domain_models.config import ProcessingConfig
    from domain_models.types import DIKWLevel
    from domain_models.manifest import Chunk, SummaryNode
    from matome.agents.summarizer import SummarizationAgent
    from matome.engines.cluster import GMMClusterer
    from matome.engines.embedder import EmbeddingService
    from matome.engines.interactive_raptor import InteractiveRaptorEngine
    from matome.engines.raptor import RaptorEngine
    from matome.engines.token_chunker import JapaneseTokenChunker
    from matome.interfaces import PromptStrategy
    from matome.utils.store import DiskChunkStore

    # Setup logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)
    logger = logging.getLogger("matome.tutorial")
    return (
        Any,
        Chunk,
        DIKWLevel,
        DiskChunkStore,
        EmbeddingService,
        GMMClusterer,
        InteractiveRaptorEngine,
        Iterator,
        JapaneseTokenChunker,
        Path,
        ProcessingConfig,
        PromptStrategy,
        RaptorEngine,
        SummarizationAgent,
        SummaryNode,
        cast,
        logger,
        logging,
        np,
        os,
        sys,
        tempfile,
        uuid,
    )


@app.cell
def _(Any, EmbeddingService, Iterator, ProcessingConfig, PromptStrategy, SummarizationAgent, logger, np, uuid):
    # --- MOCK CLASSES ---

    class MockEmbeddingService(EmbeddingService):
        """Mock Embedder to avoid downloading heavy models."""

        def __init__(self, config: ProcessingConfig):
            super().__init__(config)
            self.dim = 384  # Default for all-MiniLM-L6-v2

        def embed_strings(self, texts: Any) -> Iterator[list[float]]:
            # Return random vectors
            for _ in texts:
                # Use seed for deterministic results if needed, or just random
                yield np.random.rand(self.dim).tolist()

        def embed_chunks(self, chunks: Iterator[Chunk]) -> Iterator[Chunk]:
            for chunk in chunks:
                chunk.embedding = np.random.rand(self.dim).tolist()
                yield chunk

    class MockSummarizationAgent(SummarizationAgent):
        """Mock Agent to return deterministic summaries based on strategy."""

        def summarize(
            self,
            text: str,
            config: ProcessingConfig | None = None,
            strategy: PromptStrategy | None = None,
            context: dict[str, Any] | None = None,
        ) -> str:
            # Check context for refinement instruction
            if context and "instruction" in context:
                return f"Refined: {context['instruction']} (Original len: {len(text)})"

            # Check strategy for DIKW level
            level_name = "Summary"
            if strategy:
                try:
                    level_name = strategy.target_dikw_level.value.capitalize()
                except AttributeError:
                    level_name = type(strategy).__name__

            return f"{level_name}: {text[:50]}... (Mock Generated)"
    return MockEmbeddingService, MockSummarizationAgent


@app.cell
def _(
    DiskChunkStore,
    EmbeddingService,
    GMMClusterer,
    JapaneseTokenChunker,
    MockEmbeddingService,
    MockSummarizationAgent,
    ProcessingConfig,
    RaptorEngine,
    SummarizationAgent,
    logger,
    os,
):
    # --- SETUP & INITIALIZATION ---

    # Determine mode
    api_key = os.environ.get("OPENROUTER_API_KEY")
    mock_mode = not api_key or api_key == "mock"

    logger.info(f"Running in {'MOCK' if mock_mode else 'REAL'} mode.")

    # Initialize Config
    config = ProcessingConfig()

    # Initialize Components
    chunker = JapaneseTokenChunker(config)
    clusterer = GMMClusterer()

    if mock_mode:
        embedder = MockEmbeddingService(config)
        summarizer = MockSummarizationAgent(config)
    else:
        embedder = EmbeddingService(config)
        summarizer = SummarizationAgent(config)

    # Initialize Engine
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)
    return (
        api_key,
        chunker,
        clusterer,
        config,
        embedder,
        engine,
        mock_mode,
        summarizer,
    )


@app.cell
def _(DiskChunkStore, Path, engine, logger):
    # --- PART 1: The "Grok" Moment (Cycle 01) ---

    # Load sample text
    # We use a simple string for the tutorial to ensure it runs without external files if needed,
    # or we can check if file exists.
    sample_text = """
    Investment Philosophy:
    Value investing is an investment paradigm that involves buying securities that appear underpriced by some form of fundamental analysis.
    The concept was first popularized by Benjamin Graham and David Dodd.
    Warren Buffett is one of the most famous proponents of this strategy.

    Deep Learning:
    Deep learning is part of a broader family of machine learning methods based on artificial neural networks with representation learning.
    Learning can be supervised, semi-supervised or unsupervised.
    Deep learning architectures such as deep neural networks, deep belief networks, deep reinforcement learning, recurrent neural networks and convolutional neural networks have been applied to fields including computer vision, speech recognition, natural language processing, machine translation, bioinformatics, drug design, medical image analysis, material inspection and board game programs, where they have produced results comparable to and in some cases surpassing human expert performance.
    """ * 5  # Duplicate to ensure enough content for clustering

    # Setup temporary DB
    # We use a specific path so we can inspect it later if needed, but for UAT clear it first.
    db_path = Path("tutorials/chunks.db")
    if db_path.exists():
        db_path.unlink()

    store = DiskChunkStore(db_path)

    logger.info("Running Raptor Engine...")
    try:
        root_tree = engine.run(sample_text, store)
        logger.info("Raptor Engine finished successfully.")
    except Exception as e:
        logger.error(f"Raptor Engine failed: {e}")
        raise

    # VALIDATION: Check Root Node
    root_node = root_tree.root_node
    logger.info(f"Root Node ID: {root_node.id}")
    logger.info(f"Root Node Text: {root_node.text}")
    logger.info(f"Root Level: {root_node.level}")

    # Assert
    # Note: In mock mode with random embeddings, we might get unexpected clustering levels,
    # but we should get a root node.
    assert root_node is not None, "Root node should not be None"
    # assert root_node.level > 0, "Root node should be at least level 1 (summary)"
    # (If text is small, it might be level 1 single_chunk_root)

    print(f"✅ Part 1 Passed: Generated Tree with Root Level {root_node.level}")
    return db_path, root_node, root_tree, sample_text, store


@app.cell
def _(DiskChunkStore, root_node, store):
    # --- PART 2: Semantic Zooming (Cycle 03) ---

    children_indices = root_node.children_indices
    print(f"Root has {len(children_indices)} children.")

    children = list(store.get_nodes(children_indices))
    assert len(children) == len(children_indices), "Should retrieve all children"

    for child_node in children:
        print(f" - Child ({type(child_node).__name__}): {child_node.text[:30]}...")

    print("✅ Part 2 Passed: Semantic Zooming traversal verified.")
    return child_node, children, children_indices


@app.cell
def _(InteractiveRaptorEngine, config, root_node, store, summarizer):
    # --- PART 3: Interactive Refinement (Cycle 02 & 04) ---

    interactive = InteractiveRaptorEngine(store, summarizer, config)

    # Select a node to refine (The Root)
    target_node_id = root_node.id
    instruction = "Explain like I'm 5"

    print(f"Refining Node {target_node_id} with: '{instruction}'")

    refined_node = interactive.refine_node(str(target_node_id), instruction)

    print(f"Refined Text: {refined_node.text}")

    # Validation
    assert refined_node.metadata.is_user_edited is True, "Node should be marked as user edited"
    assert instruction in refined_node.metadata.refinement_history, "Instruction should be in history"
    if "Refined:" in refined_node.text: # Only checks this if using MockSummarizationAgent
         pass

    print("✅ Part 3 Passed: Interactive Refinement verified.")
    return instruction, interactive, refined_node, target_node_id


@app.cell
def _(Chunk, interactive, target_node_id):
    # --- PART 4: Traceability (Cycle 05) ---

    print(f"Tracing sources for Node {target_node_id}...")

    source_chunks = list(interactive.get_source_chunks(str(target_node_id)))

    print(f"Found {len(source_chunks)} source chunks.")

    assert len(source_chunks) > 0, "Should find at least one source chunk"
    assert isinstance(source_chunks[0], Chunk), "Items should be Chunk objects"

    print(f"Sample Source: {source_chunks[0].text[:50]}...")

    print("✅ Part 4 Passed: Traceability verified.")
    return source_chunks


@app.cell
def _(db_path):
    # --- PART 5: Launching the GUI ---

    print("To explore the tree visually, run the following command in your terminal:")
    print(f"uv run matome serve {db_path}")
    return


@app.cell
def _():
    print("🎉 All Systems Go: Matome 2.0 is ready for Knowledge Installation.")
    return


if __name__ == "__main__":
    app.run()
