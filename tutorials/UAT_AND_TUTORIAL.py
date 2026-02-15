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

    import matplotlib.pyplot as plt
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
    from matome.exporters.markdown import export_to_markdown
    from matome.exporters.obsidian import ObsidianCanvasExporter

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
        ObsidianCanvasExporter,
        Path,
        ProcessingConfig,
        PromptStrategy,
        RaptorEngine,
        SummarizationAgent,
        SummaryNode,
        cast,
        export_to_markdown,
        logger,
        logging,
        np,
        os,
        plt,
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
                # Use seed for deterministic results
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

    # Ensure tutorials directory exists
    os.makedirs("tutorials", exist_ok=True)

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
def _(chunker, config, logger):
    # --- SCENARIO 1: Quickstart (The Basics) ---
    logger.info("Starting SCENARIO 1: Quickstart")

    # Sample text (simulating a financial document)
    SAMPLE_TEXT = """
    【投資哲学】
    バリュー投資は、何らかのファンダメンタル分析により過小評価されていると思われる証券を購入する投資手法である。
    この概念はベンジャミン・グレアムとデビッド・ドッドによって最初に広められた。
    ウォーレン・バフェットはこの戦略の最も有名な支持者の一人である。

    【ディープラーニング】
    ディープラーニングは、表現学習を伴う人工ニューラルネットワークに基づく機械学習手法の広範なファミリーの一部である。
    学習は、教師あり、半教師あり、または教師なしで行うことができる。
    ディープニューラルネットワーク、ディープビリーフネットワーク、深層強化学習、リカレントニューラルネットワーク、畳み込みニューラルネットワークなどのディープラーニングアーキテクチャは、コンピュータビジョン、音声認識、自然言語処理、機械翻訳、バイオインフォマティクス、創薬、医療画像分析、材料検査、ボードゲームプログラムなどの分野に適用され、人間の専門家のパフォーマンスに匹敵し、場合によってはそれを超える結果を生み出している。

    【四季報の読み方】
    会社四季報は、日本の全上場企業のデータブックである。
    業績予想、財務状況、株主構成などが記載されている。
    特に重要なのは「業績欄」であり、売上高や営業利益の推移を確認することで、企業の成長性を判断できる。
    また、「材料欄」には、新製品の開発状況や提携話など、将来の株価に影響を与える可能性のある情報が記載されていることが多い。
    PER（株価収益率）やPBR（株価純資産倍率）などの指標も重要であるが、これらはあくまで過去の実績に基づくものであり、将来の成長性を加味して判断する必要がある。
    """ * 3  # Duplicate to ensure enough content for chunking

    # 1. Chunking
    chunks = list(chunker.split_text(SAMPLE_TEXT, config))
    logger.info(f"Generated {len(chunks)} chunks.")

    # 2. Visualize Chunks
    print("--- First 5 Chunks ---")
    for i, chunk in enumerate(chunks[:5]):
        print(f"Chunk {i}: {chunk.text.strip()[:50]}...")

    assert len(chunks) > 0, "Should generate chunks"

    print("✅ SCENARIO 1 Passed: Text ingested and chunked.")
    return SAMPLE_TEXT, chunks, i


@app.cell
def _(chunks, clusterer, embedder, logger, plt):
    # --- SCENARIO 2: Clustering Deep Dive (The Engine) ---
    logger.info("Starting SCENARIO 2: Clustering Deep Dive")

    # 1. Generate Embeddings
    # Note: embedder.embed_chunks yields chunks with embeddings populated
    embedded_chunks = list(embedder.embed_chunks(iter(chunks)))
    logger.info("Embeddings generated.")

    # 2. Run Clustering
    # We manually trigger clustering to visualize it
    # GMMClusterer expects chunks with embeddings
    # Note: GMMClusterer.cluster returns (clusters, global_embeddings)
    # But wait, RaptorEngine handles this. Let's inspect GMMClusterer.
    # We can just inspect the embeddings for visualization since clustering logic is internal

    # Extract embeddings for visualization
    embeddings = [c.embedding for c in embedded_chunks if c.embedding]

    if len(embeddings) >= 2:
        # Visualize 2D projection
        # We use PCA for simplicity here (mocking UMAP)
        from sklearn.decomposition import PCA

        pca = PCA(n_components=2)
        coords = pca.fit_transform(embeddings)

        plt.figure(figsize=(8, 6))
        plt.scatter(coords[:, 0], coords[:, 1], alpha=0.5)
        plt.title("Chunk Embeddings Projection (PCA)")
        plt.xlabel("Component 1")
        plt.ylabel("Component 2")
        plt.grid(True)
        # In a real notebook, this would show the plot. In headless, we save it.
        plt.savefig("tutorials/clustering_visualization.png")
        logger.info("Clustering visualization saved to tutorials/clustering_visualization.png")
    else:
        logger.warning("Not enough embeddings to visualize.")

    print("✅ SCENARIO 2 Passed: Embeddings generated and visualized.")
    return embedded_chunks, embeddings


@app.cell
def _(DiskChunkStore, Path, SAMPLE_TEXT, engine, export_to_markdown, logger):
    # --- SCENARIO 3: Full Raptor Pipeline (The "Aha!" Moment) ---
    logger.info("Starting SCENARIO 3: Full Raptor Pipeline")

    # Setup temporary DB
    db_path = Path("tutorials/chunks.db")
    if db_path.exists():
        db_path.unlink()

    store = DiskChunkStore(db_path)

    # Run Engine
    try:
        root_tree = engine.run(SAMPLE_TEXT, store)
        logger.info("Raptor Engine finished successfully.")
    except Exception as e:
        logger.error(f"Raptor Engine failed: {e}")
        raise

    # Validation
    root_node = root_tree.root_node
    logger.info(f"Root Node Level: {root_node.level}")

    # Export to Markdown
    md_output = export_to_markdown(root_tree, store)
    with open("summary_all.md", "w", encoding="utf-8") as f:
        f.write(md_output)

    logger.info("Exported summary to summary_all.md")

    assert Path("summary_all.md").exists(), "Markdown file should exist"
    assert len(md_output) > 0, "Markdown content should not be empty"

    print("✅ SCENARIO 3 Passed: Pipeline executed and Markdown exported.")
    return db_path, md_output, root_node, root_tree, store


@app.cell
def _(ObsidianCanvasExporter, Path, config, logger, root_tree, store):
    # --- SCENARIO 4: KJ Method Visualization (The Output) ---
    logger.info("Starting SCENARIO 4: KJ Method Visualization")

    exporter = ObsidianCanvasExporter(config)
    output_path = Path("summary_kj.canvas")

    exporter.export(root_tree, output_path, store)

    logger.info(f"Exported Canvas to {output_path}")

    assert output_path.exists(), "Canvas file should exist"

    print("✅ SCENARIO 4 Passed: Obsidian Canvas exported.")
    return exporter, output_path


@app.cell
def _(
    Chunk,
    InteractiveRaptorEngine,
    config,
    root_node,
    store,
    summarizer,
):
    # --- BONUS: Interactive Refinement & Traceability ---

    # Interactive Refinement
    interactive = InteractiveRaptorEngine(store, summarizer, config)
    target_node_id = root_node.id
    instruction = "Explain like I'm 5"

    refined_node = interactive.refine_node(str(target_node_id), instruction)

    assert refined_node.metadata.is_user_edited is True
    assert instruction in refined_node.metadata.refinement_history

    print(f"Refined Node: {refined_node.text[:50]}...")
    print("✅ Interactive Refinement Verified.")

    # Traceability
    source_chunks = list(interactive.get_source_chunks(str(target_node_id)))
    assert len(source_chunks) > 0
    assert isinstance(source_chunks[0], Chunk)

    print(f"Traced {len(source_chunks)} source chunks.")
    print("✅ Traceability Verified.")
    return (
        instruction,
        interactive,
        refined_node,
        source_chunks,
        target_node_id,
    )


@app.cell
def _(db_path):
    print("🎉 All Scenarios Passed!")
    print(f"To explore the tree visually, run: uv run matome serve {db_path}")
    return


if __name__ == "__main__":
    app.run()
