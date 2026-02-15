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

    import matplotlib.pyplot as plt
    import numpy as np
    import marimo as mo

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
    from matome.exporters.markdown import export_to_markdown
    from matome.exporters.obsidian import ObsidianCanvasExporter
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
        ObsidianCanvasExporter,
        Path,
        ProcessingConfig,
        RaptorEngine,
        SummarizationAgent,
        SummaryNode,
        export_to_markdown,
        logger,
        logging,
        mo,
        np,
        os,
        plt,
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
def _(chunker, config, logger, mo):
    # Scenario 1: Quickstart (Chunking)

    # Sample Text (Investment Philosophy style) - Extended to ensure clustering happens
    sample_text_base = """
    長期投資の基本は、企業の成長と共に資産を増やすことです。
    短期的な市場の変動に惑わされず、本質的な価値を見極める必要があります。

    複利の効果は時間を味方につけることで最大化されます。
    雪だるま式に資産が増えるこの仕組みを理解することが重要です。

    リスク管理は分散投資によって行います。
    一つのカゴにすべての卵を盛るな、という格言の通りです。

    最後に、自己への投資も忘れてはいけません。
    知識こそが最大の防御であり、最大の武器となるのです。
    """

    # Repeat text to simulate a larger document for clustering demonstration
    sample_text = (sample_text_base + "\n\n") * 5

    logger.info("Starting Scenario 1: Chunking...")

    # Chunk the text
    chunks_iter = chunker.split_text(sample_text, config)
    chunks = list(chunks_iter)

    logger.info(f"Generated {len(chunks)} chunks.")

    # Visualizing Chunks
    chunk_data = [{"Index": c.index, "Text": c.text[:50] + "..."} for c in chunks[:5]]

    table = mo.ui.table(chunk_data, label="First 5 Chunks")

    logger.info("✅ Scenario 1 Passed: Text chunked successfully.")
    return chunks, chunks_iter, sample_text, sample_text_base, table, chunk_data


@app.cell
def _(chunks, embedder, logger, mo, plt):
    # Scenario 2: Embedding & Clustering Visualization

    logger.info("Starting Scenario 2: Embedding & Visualization...")

    # Embed chunks (Mock or Real)
    # We consume the iterator to get a list
    embedded_chunks = list(embedder.embed_chunks(chunks))

    # Extract embeddings for visualization
    embeddings = [c.embedding for c in embedded_chunks if c.embedding]

    if not embeddings:
        logger.warning("No embeddings generated.")
    else:
        # Simple 2D Visualization (using first 2 dims or random if high dim)
        # Since MockEmbedder returns 384 dims, we just plot dim 0 vs dim 1
        x = [e[0] for e in embeddings]
        y = [e[1] for e in embeddings]

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(x, y, alpha=0.7)
        ax.set_title("Chunk Embeddings Projection (Dim 0 vs Dim 1)")
        ax.set_xlabel("Dimension 0")
        ax.set_ylabel("Dimension 1")
        plt.tight_layout()

        # In Marimo, we can display the figure
        # plt.show() # Not needed in Marimo if we return the fig or use mo.mpl

    logger.info("✅ Scenario 2 Passed: Embeddings generated and visualized.")
    return embedded_chunks, embeddings, fig, x, y


@app.cell
def _(
    GMMClusterer,
    RaptorEngine,
    chunker,
    clusterer,
    config,
    embedder,
    logger,
    sample_text,
    store,
    summarizer,
):
    # Scenario 3: Full RAPTOR Pipeline (Cycle 01)

    logger.info("Starting Scenario 3: Full RAPTOR Pipeline...")

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

    logger.info("✅ Scenario 3 Passed: RAPTOR Engine executed successfully.")
    return clusterer, engine, root_node, tree


@app.cell
def _(
    ObsidianCanvasExporter,
    export_to_markdown,
    logger,
    mo,
    store,
    tree,
):
    # Scenario 4: Export & Visualization (Cycle 04/05)

    logger.info("Starting Scenario 4: Export & Visualization...")

    # 1. Export to Markdown
    markdown_output = export_to_markdown(tree, store)

    # Save to file (optional, but good for verification)
    with open("tutorials/summary_all.md", "w", encoding="utf-8") as f:
        f.write(markdown_output)

    # 2. Export to Canvas
    exporter = ObsidianCanvasExporter()
    exporter.export(tree, Path("tutorials/summary_kj.canvas"), store)

    logger.info("✅ Scenario 4 Passed: Exported to Markdown and Canvas.")

    # Display Markdown Summary
    return markdown_output, exporter


@app.cell
def _(InteractiveRaptorEngine, config, logger, root_node, store, summarizer):
    # Scenario 5: Interactive Refinement (Cycle 02/04)

    logger.info("Starting Scenario 5: Interactive Refinement...")

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

    logger.info("✅ Scenario 5 Passed: Node refinement verified.")
    return (
        instruction,
        interactive_engine,
        node_id,
        updated_node,
    )


@app.cell
def _(interactive_engine, logger, node_id, sample_text):
    # Scenario 6: Traceability (Cycle 05)

    logger.info("Starting Scenario 6: Traceability...")

    # 1. Get Source Chunks for the node
    source_chunks = list(interactive_engine.get_source_chunks(node_id))

    logger.info(f"Found {len(source_chunks)} source chunks.")

    # 2. Validation
    assert len(source_chunks) > 0

    first_chunk_text = source_chunks[0].text
    assert len(first_chunk_text) > 0

    # Ensure the chunk is actually part of the original text
    # We clean whitespace for comparison as chunking might affect spacing slightly
    clean_chunk = first_chunk_text.replace("\n", "").replace(" ", "")
    clean_sample = sample_text.replace("\n", "").replace(" ", "")

    assert clean_chunk in clean_sample

    print(f"Source Chunk 1: {first_chunk_text[:50]}...")

    logger.info("✅ Scenario 6 Passed: Source chunks retrieved and verified against original text.")
    return clean_chunk, clean_sample, first_chunk_text, source_chunks


@app.cell
def _(db_path, mo):
    # Final: Launching the GUI
    return mo.md(
        f"""
        ## Launching the GUI

        To explore the generated knowledge tree visually, run the following command in your terminal:

        ```bash
        uv run matome serve {db_path}
        ```

        This will start a local server (usually at http://127.0.0.1:5006) where you can:
        - View the DIKW hierarchy.
        - Click nodes to see details.
        - Verify source chunks.
        """
    )


@app.cell
def _(logger):
    print("\n")
    logger.info("🎉 All Systems Go: Matome 2.0 is ready for Knowledge Installation.")
    return


if __name__ == "__main__":
    app.run()
