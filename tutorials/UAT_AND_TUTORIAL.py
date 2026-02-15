import marimo

__generated_with = "0.1.0"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo
    import os
    import sys
    import random
    import numpy as np
    from pathlib import Path
    from typing import Iterator, Iterable

    # Robust project root finding
    cwd = Path.cwd()
    if (cwd / "src").is_dir():
        project_root = cwd
    elif (cwd.parent / "src").is_dir():
        project_root = cwd.parent
    else:
        # Fallback to assuming we are in tutorials/ and src is in ../src
        project_root = cwd.parent

    if str(project_root / "src") not in sys.path:
        sys.path.append(str(project_root / "src"))

    from domain_models.config import ProcessingConfig
    from domain_models.manifest import Chunk, SummaryNode
    from matome.engines.token_chunker import JapaneseTokenChunker
    from matome.engines.embedder import EmbeddingService
    from matome.engines.cluster import GMMClusterer
    from matome.engines.raptor import RaptorEngine
    from matome.agents.summarizer import SummarizationAgent
    from matome.exporters.obsidian import ObsidianCanvasExporter
    from matome.utils.store import DiskChunkStore

    # Setup directories
    test_data_dir = project_root / "test_data"
    test_data_dir.mkdir(exist_ok=True)

    tutorials_dir = project_root / "tutorials"
    tutorials_dir.mkdir(exist_ok=True)

    # Create dummy files if not exist in test_data
    sample_txt = test_data_dir / "sample.txt"
    if not sample_txt.exists():
        sample_txt.write_text("これはサンプルのテキストです。Matome 2.0のテスト用です。\n\n二つ目の段落です。日本語のチャンキングをテストします。")

    full_txt = test_data_dir / "エミン流「会社四季報」最強の読み方.txt"
    if not full_txt.exists():
        # Create a longer dummy text
        dummy_content = "これは長いドキュメントのシミュレーションです。\n" * 100
        full_txt.write_text(dummy_content)

    return (
        mo,
        os,
        sys,
        random,
        np,
        Path,
        Iterator,
        Iterable,
        ProcessingConfig,
        Chunk,
        SummaryNode,
        JapaneseTokenChunker,
        EmbeddingService,
        GMMClusterer,
        RaptorEngine,
        SummarizationAgent,
        ObsidianCanvasExporter,
        DiskChunkStore,
        test_data_dir,
        tutorials_dir,
        sample_txt,
        full_txt,
    )


@app.cell
def __(os, mo):
    # Determine Mode
    api_key = os.getenv("OPENROUTER_API_KEY")
    mock_mode = not bool(api_key)

    mode_msg = "Running in **MOCK MODE** (No API Key detected)" if mock_mode else "Running in **REAL MODE**"
    mo.md(f"""
    # Matome 2.0 UAT & Tutorial

    {mode_msg}

    This notebook validates the core functionality of Matome 2.0:
    1.  **Quickstart**: Text Chunking
    2.  **Clustering**: Embedding & GMM
    3.  **Raptor Pipeline**: Recursive Summarization
    4.  **Visualization**: Obsidian Canvas Export
    """)
    return api_key, mock_mode


@app.cell
def __(
    ProcessingConfig,
    EmbeddingService,
    SummarizationAgent,
    Iterator,
    Iterable,
    Chunk,
    np,
    mock_mode,
):
    # Mock Classes definition

    class MockEmbeddingService(EmbeddingService):
        """Mock embedding service returning random vectors."""
        def __init__(self, config: ProcessingConfig):
            super().__init__(config)
            self.dim = 384 # Default dimension for all-MiniLM-L6-v2

        def embed_strings(self, texts: Iterable[str]) -> Iterator[list[float]]:
            for _ in texts:
                # Return random vector
                yield np.random.rand(self.dim).tolist()

        def embed_chunks(self, chunks: Iterable[Chunk]) -> Iterator[Chunk]:
            for chunk in chunks:
                chunk.embedding = np.random.rand(self.dim).tolist()
                yield chunk

    class MockSummarizationAgent(SummarizationAgent):
        """Mock summarization agent."""
        def __init__(self, config: ProcessingConfig):
            # Bypass super init that checks API key
            self.config = config
            self.model_name = config.summarization_model
            self.mock_mode = True
            self.llm = None

        def summarize(self, text, config=None, strategy=None, context=None):
            return f"Summary of: {text[:20]}..."

    # Factory to get services
    def get_services(config: ProcessingConfig):
        if mock_mode:
            return MockEmbeddingService(config), MockSummarizationAgent(config)

        # Real mode
        # Note: EmbeddingService loads model which might be slow, but okay for Real mode UAT
        return EmbeddingService(config), SummarizationAgent(config)

    return MockEmbeddingService, MockSummarizationAgent, get_services


@app.cell
def __(ProcessingConfig, JapaneseTokenChunker, sample_txt, mo):
    # Scenario 1: Quickstart (Chunking)
    mo.md("## 1. Quickstart: Chunking")

    config = ProcessingConfig()
    chunker = JapaneseTokenChunker(config)

    text = sample_txt.read_text()
    chunks = list(chunker.split_text(text, config))

    mo.md(f"**Loaded {len(text)} chars.**\n**Generated {len(chunks)} chunks.**\n\nFirst chunk: `{chunks[0].text if chunks else 'None'}`")
    return chunker, text, chunks, config


@app.cell
def __(
    ProcessingConfig,
    GMMClusterer,
    get_services,
    chunks,
    mo,
    mock_mode
):
    # Scenario 2: Clustering
    mo.md("## 2. Clustering Engine")

    # We need embeddings first
    cluster_config = ProcessingConfig()
    embedder, _ = get_services(cluster_config)

    # Embed chunks (using generator to simulate streaming)
    # We iterate and collect to pass to clusterer which expects iterable of (id, vec)

    embedded_chunks = list(embedder.embed_chunks(chunks))

    # Prepare input for clusterer: Iterable[tuple[NodeID, list[float]]]
    # chunk.index is int, clusterer expects NodeID (str|int)
    embeddings_input = [(c.index, c.embedding) for c in embedded_chunks]

    clusterer = GMMClusterer()
    clusters = clusterer.cluster_nodes(embeddings_input, cluster_config)

    mo.md(f"**Generated {len(clusters)} clusters.** from {len(embedded_chunks)} chunks.")
    return cluster_config, embedder, embedded_chunks, embeddings_input, clusterer, clusters


@app.cell
def __(
    ProcessingConfig,
    RaptorEngine,
    GMMClusterer,
    get_services,
    full_txt,
    chunker,
    clusterer,
    mo,
    mock_mode,
    DiskChunkStore,
    tutorials_dir
):
    # Scenario 3: Raptor Pipeline
    mo.md("## 3. Raptor Pipeline")

    raptor_config = ProcessingConfig()
    embedder_service, summarizer_service = get_services(raptor_config)

    engine = RaptorEngine(
        chunker=chunker,
        embedder=embedder_service,
        clusterer=clusterer,
        summarizer=summarizer_service,
        config=raptor_config
    )

    text_content = full_txt.read_text()

    # Run Raptor with persistent Store in tutorials/ directory
    db_path = tutorials_dir / "chunks.db"
    if db_path.exists():
        db_path.unlink()

    store = DiskChunkStore(db_path=db_path)

    try:
        # Pass store to run() to ensure data is persisted in our DB
        tree = engine.run(text_content, store=store)

        summary_path = tutorials_dir / "summary_all.md"
        summary_path.write_text(tree.root_node.text)

        result_msg = f"**Pipeline Complete!**\nRoot Summary Length: {len(tree.root_node.text)}\nSaved to `{summary_path}`"
    except Exception as e:
        result_msg = f"**Pipeline Failed**: {e}"
        # Cleanup if failed
        store.close()
        raise e

    mo.md(result_msg)
    return raptor_config, engine, text_content, tree, summary_path, result_msg, store, db_path


@app.cell
def __(
    ObsidianCanvasExporter,
    tree,
    raptor_config,
    tutorials_dir,
    store,
    mo
):
    # Scenario 4: Visualization
    mo.md("## 4. KJ Method Visualization (Obsidian Canvas)")

    exporter = ObsidianCanvasExporter(raptor_config)
    output_path = tutorials_dir / "summary_kj.canvas"

    # Use the same store from previous step which contains the data
    exporter.export(tree, output_path, store)

    # Close store when done
    store.close()

    mo.md(f"**Exported to `{output_path}`**\n\nYou can open this file in Obsidian.")
    return exporter, output_path


if __name__ == "__main__":
    app.run()
