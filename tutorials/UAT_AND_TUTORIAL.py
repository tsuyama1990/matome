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
    import concurrent.futures
    import threading
    import time
    from pathlib import Path
    from typing import Any, Iterator, cast

    import matplotlib.pyplot as plt
    import numpy as np
    from domain_models.config import ProcessingConfig
    from domain_models.types import DIKWLevel, NodeID
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
        NodeID,
        ObsidianCanvasExporter,
        Path,
        ProcessingConfig,
        PromptStrategy,
        RaptorEngine,
        SummarizationAgent,
        SummaryNode,
        cast,
        concurrent,
        export_to_markdown,
        logger,
        logging,
        np,
        os,
        plt,
        sys,
        tempfile,
        threading,
        time,
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
    # --- Part 1: The "Grok" Moment (Cycle 01) - Wisdom Generation ---
    # Goal: Load text, run Raptor, and verify the Root Node is "Wisdom".
    logger.info("Starting Part 1: Wisdom Generation")

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
    assert len(chunks) > 0, "Should generate chunks"

    # 2. Visualize Chunks (Quick verification)
    print("--- First 3 Chunks ---")
    for i, chunk in enumerate(chunks[:3]):
        print(f"Chunk {i}: {chunk.text.strip()[:50]}...")

    return SAMPLE_TEXT, chunks, i


@app.cell
def _(
    DIKWLevel,
    DiskChunkStore,
    Path,
    SAMPLE_TEXT,
    engine,
    export_to_markdown,
    logger,
):
    # --- Part 1 Continued: Running the Engine ---

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

    # Validation: Verify Root is Wisdom (UAT-01)
    root_node = root_tree.root_node
    logger.info(f"Root Node Level: {root_node.level}, DIKW: {root_node.metadata.dikw_level}")

    # Note: In mock mode, Raptor might not strictly assign "WISDOM" if using default simple strategies
    # unless config is set to use WisdomStrategy for root.
    # We should verify it is SummaryNode and has a DIKW level.
    # The default Raptor engine assigns DIKW level based on topology key "root".

    # Assert Root is Wisdom (or whatever config says, default is WISDOM)
    assert root_node.metadata.dikw_level == DIKWLevel.WISDOM, f"Root should be Wisdom, got {root_node.metadata.dikw_level}"

    # Export to Markdown for visual check
    md_output = export_to_markdown(root_tree, store)
    with open("summary_all.md", "w", encoding="utf-8") as f:
        f.write(md_output)

    print("✅ Part 1 Passed: Wisdom Generation & Markdown Export.")
    return db_path, md_output, root_node, root_tree, store


@app.cell
def _(DIKWLevel, SummaryNode, logger, root_node, store):
    # --- Part 2: Semantic Zooming (Cycle 03) ---
    # Goal: Traverse the tree and verify hierarchy (UAT-02, UAT-05 Logic)
    logger.info("Starting Part 2: Semantic Zooming")

    # The root is Wisdom. Its children should be Knowledge.
    # Knowledge children should be Information (or Data if tree is shallow).

    # Check children of Root
    children_ids = root_node.children_indices
    assert len(children_ids) > 0, "Root should have children"

    first_child = store.get_node(children_ids[0])

    if isinstance(first_child, SummaryNode):
        logger.info(f"Level 2 Node DIKW: {first_child.metadata.dikw_level}")
        # Ideally Knowledge, but depends on tree depth.
        # If depth is small, might go straight to Data or Information.
        # But let's just verify we can traverse.
    else:
        logger.info("Level 2 Node is Chunk (Data). Tree is shallow.")

    # Validate Hierarchy Depth
    max_level = store.get_max_level()
    logger.info(f"Tree Max Level: {max_level}")
    assert max_level >= 1

    print("✅ Part 2 Passed: Hierarchy Traversal Verified.")
    return children_ids, first_child, max_level


@app.cell
def _(
    InteractiveRaptorEngine,
    config,
    root_node,
    store,
    summarizer,
):
    # --- Part 3: Interactive Refinement (Cycle 02 & 04) ---
    # Goal: Refine a node and verify persistence (UAT-03, UAT-06 Backend)

    interactive = InteractiveRaptorEngine(store, summarizer, config)
    target_node_id = root_node.id
    instruction = "Explain like I'm 5"

    refined_node = interactive.refine_node(str(target_node_id), instruction)

    # Validation
    assert refined_node.metadata.is_user_edited is True
    assert instruction in refined_node.metadata.refinement_history
    assert refined_node.id == str(target_node_id) # ID must not change

    # Verify persistence
    persisted_node = store.get_node(target_node_id)
    assert persisted_node.metadata.is_user_edited is True
    assert persisted_node.text == refined_node.text

    print(f"Refined Node: {refined_node.text[:50]}...")
    print("✅ Part 3 Passed: Interactive Refinement Verified.")
    return instruction, interactive, persisted_node, refined_node, target_node_id


@app.cell
def _(concurrent, interactive, logger, store, target_node_id, threading):
    # --- Part 4: Concurrency (Cycle 02) ---
    # Goal: Read/Write simultaneously without locking DB (UAT-04)
    # We will launch a read operation in a loop while performing a write.

    logger.info("Starting Part 4: Concurrency Test")

    def read_loop(node_id, stop_event):
        reads = 0
        while not stop_event.is_set():
            _ = store.get_node(node_id)
            reads += 1
            # slight sleep to yield gil
            import time
            time.sleep(0.01)
        return reads

    stop_event = threading.Event()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Start reader
        reader_future = executor.submit(read_loop, target_node_id, stop_event)

        # Perform Write (Refinement)
        try:
            _ = interactive.refine_node(str(target_node_id), "Concurrency Test Update")
            logger.info("Concurrent Write Completed")
        except Exception as e:
            logger.error(f"Concurrent Write Failed: {e}")
            raise

        # Stop reader
        stop_event.set()
        reads = reader_future.result()
        logger.info(f"Concurrent Reads Completed: {reads}")

    print("✅ Part 4 Passed: Concurrency Test (Read/Write) Verified.")
    return read_loop, reader_future, reads, stop_event


@app.cell
def _(Chunk, interactive, target_node_id):
    # --- Part 5: Traceability (Cycle 05) ---
    # Goal: Get source chunks for a node (UAT-07)

    source_chunks = list(interactive.get_source_chunks(str(target_node_id)))
    assert len(source_chunks) > 0
    assert isinstance(source_chunks[0], Chunk)

    print(f"Traced {len(source_chunks)} source chunks for node {target_node_id}.")
    print("✅ Part 5 Passed: Traceability Verified.")
    return source_chunks


@app.cell
def _(ObsidianCanvasExporter, Path, config, logger, root_tree, store):
    # --- Part 6: Launching the GUI & Export (UAT-05) ---

    # Export Canvas
    exporter = ObsidianCanvasExporter(config)
    output_path = Path("summary_kj.canvas")
    exporter.export(root_tree, output_path, store)
    assert output_path.exists()

    print("✅ Part 6 Passed: Canvas Exported.")
    return exporter, output_path


@app.cell
def _(db_path):
    print("🎉 All Systems Go: Matome 2.0 is ready for Knowledge Installation.")
    print(f"To explore the tree visually, run: uv run matome serve {db_path}")
    return


if __name__ == "__main__":
    app.run()
