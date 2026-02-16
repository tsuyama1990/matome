import marimo

__generated_with = "0.9.14"
app = marimo.App(width="medium")


@app.cell
def __():
    import logging
    import os
    import sys
    import threading
    import time
    from pathlib import Path

    import marimo as mo

    # Ensure src is in path for local execution
    src_path = str(Path.cwd() / "src")
    if src_path not in sys.path:
        sys.path.append(src_path)

    # Setup Logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger("UAT")

    mo.md(
        """
        # Matome 2.0: User Acceptance Test & Tutorial

        Welcome to the executable tutorial for **Matome 2.0**. This notebook serves two purposes:
        1.  **Interactive Guide**: Learn how to use the system step-by-step.
        2.  **Automated UAT**: Verify that the core engines (Batch & Interactive) are working correctly.

        **Note:** If no API Key is found, we will run in **Mock Mode**.
        """
    )
    return Path, logger, logging, mo, os, sys, threading, time


@app.cell
def __(os):
    # API Key Handling
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    mock_mode = False

    if not api_key or api_key == "mock":
        os.environ["OPENROUTER_API_KEY"] = "mock"  # Force mock mode for SummarizationAgent
        mock_mode = True
        print("⚠️ No API Key found (or set to 'mock'). Running in **MOCK MODE**.")
    else:
        print("✅ API Key detected. Running in **REAL MODE**.")
    return api_key, mock_mode


@app.cell
def __(mock_mode):
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

    # 1. Configuration
    config = ProcessingConfig(
        max_input_length=100000,
        max_tokens=100,  # Small chunks to force tree depth
        overlap=10,
        max_summary_tokens=50,  # Short summaries for UAT
        clustering_algorithm="gmm", # Explicitly set
        # If in mock mode, we ensure faster processing but still correct structure
        max_retries=1 if mock_mode else 3,
    )

    # 2. Dependency Injection
    # We explicitly initialize all components as per the architecture
    chunker = JapaneseTokenChunker(config)
    embedder = EmbeddingService(config)
    clusterer = GMMClusterer()
    summarizer = SummarizationAgent(config)

    # 3. Initialize Batch Engine
    raptor = RaptorEngine(
        chunker=chunker,
        embedder=embedder,
        clusterer=clusterer,
        summarizer=summarizer,
        config=config,
    )

    print("✅ Engines Initialized")
    return (
        Chunk,
        DIKWLevel,
        DiskChunkStore,
        EmbeddingService,
        GMMClusterer,
        InteractiveRaptorEngine,
        JapaneseTokenChunker,
        ProcessingConfig,
        RaptorEngine,
        SummarizationAgent,
        SummaryNode,
        chunker,
        clusterer,
        config,
        embedder,
        raptor,
        summarizer,
    )


@app.cell
def __(mo):
    mo.md("## Part 1: The 'Grok' Moment (Cycle 01)")


@app.cell
def __(DiskChunkStore, Path, config, mock_mode, raptor):
    # Sample Text (Investment Philosophy)
    # We need enough text to generate at least 2 levels (Chunks -> Summaries -> Root)
    # Each chunk is roughly 100-200 tokens. We want > 5-10 chunks.

    base_text = """
    Value investing is an investment paradigm that involves buying securities that appear underpriced by some form of fundamental analysis.
    All forms of value investing derive from the philosophy of investment taught by Benjamin Graham and David Dodd at Columbia Business School in 1928.
    The concept of "margin of safety" is the principle of buying a security at a significant discount to its intrinsic value, which is thought to provide not only high-return opportunities but also to minimize the downside risk of an investment.
    Warren Buffett, a student of Graham, is a notable proponent of this strategy.

    Contrarian investing is an investment style in which investors purposefully go against prevailing market trends by selling when others are buying, and buying when others are selling.
    A contrarian investor believes that the people who say the market is going up do so only when they are fully invested and have no further purchasing power.
    At this point, the market is at a peak. When people predict a downturn, they have already sold out, at which point the market can only go up.
    """

    # Ensure enough length for clustering
    if mock_mode:
        # Repeat more times in mock mode to ensure depth without cost
        full_text = (base_text + "\n\n") * 20
    else:
        full_text = (base_text + "\n\n") * 10

    print(f"Input Text Length: {len(full_text)} chars")

    # Run RAPTOR
    # Use a persistent file for UAT to inspect later
    db_path = Path("tutorials/chunks.db")
    if db_path.exists():
        db_path.unlink() # Start fresh

    store = DiskChunkStore(db_path)

    print("🚀 Running RAPTOR Engine... (This may take a moment)")
    tree = raptor.run(full_text, store=store)

    print("✅ Tree Generation Complete.")
    print(f"Root Node ID: {tree.root_node.id}")
    print(f"Tree Levels: {tree.metadata.get('levels')}")

    return base_text, db_path, full_text, store, tree


@app.cell
def __(DIKWLevel, mo, tree):
    # Verification: UAT-01 (Wisdom Generation)
    root = tree.root_node

    print(f"Root Text: {root.text[:100]}...")
    print(f"Root Level: {root.metadata.dikw_level}")

    # Allow weak check for Mock Mode if strategy returns default or something else,
    # but normally Raptor should set Wisdom for top level.
    # We check if it is either the Enum value or the string value "wisdom"
    assert root.metadata.dikw_level == DIKWLevel.WISDOM or root.metadata.dikw_level == "wisdom", \
        f"Expected Wisdom, got {root.metadata.dikw_level}"

    mo.md(f"### 🎯 **UAT-01 Passed**: Root node is verified as **{root.metadata.dikw_level}**.")
    return root


@app.cell
def __(mo):
    mo.md("## Part 2: Semantic Zooming (Cycle 03)")


@app.cell
def __(Chunk, DIKWLevel, InteractiveRaptorEngine, config, mo, store, summarizer):
    # Initialize Interactive Engine for traversal
    interactive_engine = InteractiveRaptorEngine(
        store=store,
        summarizer=summarizer,
        config=config
    )

    # Verification: UAT-02 (Information Gen) & Semantic Zooming
    # We want to check Level 1 nodes (summaries of chunks).
    # These should be 'information' or 'knowledge' depending on depth, but definitely Summaries.

    level_1_ids = list(store.get_node_ids_by_level(1))
    print(f"Found {len(level_1_ids)} Level 1 nodes.")

    assert len(level_1_ids) > 0, "Tree must have at least one level of summaries above chunks."

    # Check a sample L1 node
    sample_l1_id = level_1_ids[0]
    sample_l1_node = store.get_node(sample_l1_id)

    print(f"Sample L1 Node Level: {sample_l1_node.metadata.dikw_level}")

    # Check children are chunks
    child_ids = sample_l1_node.children_indices
    first_child = store.get_node(child_ids[0])

    assert isinstance(first_child, Chunk), "Children of Level 1 nodes must be Chunks."

    # The DIKW level of L1 should ideally be Information (actionable) or Knowledge (structural).
    # Default config maps leaf strategy to 'information'.
    assert sample_l1_node.metadata.dikw_level in [DIKWLevel.INFORMATION, DIKWLevel.KNOWLEDGE, "information", "knowledge"], \
        f"Unexpected L1 level: {sample_l1_node.metadata.dikw_level}"

    mo.md("### 🎯 **UAT-02 Passed**: Level 1 nodes are valid Summaries of Chunks (Semantic Zoom Verified).")
    return (
        child_ids,
        first_child,
        interactive_engine,
        level_1_ids,
        sample_l1_id,
        sample_l1_node,
    )


@app.cell
def __(mo):
    mo.md("## Part 3: Interactive Refinement (Cycle 02 & 04)")


@app.cell
def __(interactive_engine, mo, root):
    # Verification: UAT-03 (Single Refinement)

    # We refine the Root for simplicity, as we know it exists.
    target_node = root

    print(f"Refining Node: {target_node.id}")
    instruction = "Explain this like I'm 5 years old."

    refined_node = interactive_engine.refine_node(target_node.id, instruction)

    print(f"Refined Text: {refined_node.text[:50]}...")
    print(f"User Edited: {refined_node.metadata.is_user_edited}")

    assert refined_node.metadata.is_user_edited is True
    assert instruction in refined_node.metadata.refinement_history
    # Text should change (even in mock mode, it returns "Summary of ...")
    assert refined_node.text != "", "Refined text shouldn't be empty"

    mo.md("### 🎯 **UAT-03 Passed**: Node successfully refined and persisted.")
    return instruction, refined_node, target_node


@app.cell
def __(interactive_engine, mo, target_node, threading, time):
    # Verification: UAT-04 (Concurrency)
    # Strategy: Spawn a thread that reads the node continuously while the main thread writes to it.

    stop_event = threading.Event()
    errors = []

    def reader_thread():
        try:
            while not stop_event.is_set():
                # Read node
                _ = interactive_engine.get_node(target_node.id)
                time.sleep(0.05)
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=reader_thread)
    t.start()

    try:
        # Perform another refinement (Write)
        print("Running concurrent refinement...")
        interactive_engine.refine_node(target_node.id, "Make it even simpler.")
        time.sleep(0.5) # Allow some reads to happen
    finally:
        stop_event.set()
        t.join()

    if errors:
        print(f"Concurrency errors encountered: {errors}")
        raise errors[0]

    mo.md("### 🎯 **UAT-04 Passed**: Concurrent Read/Write verified without crashing.")
    return errors, reader_thread, stop_event, t


@app.cell
def __(mo):
    mo.md("## Part 4: Traceability (Cycle 05)")


@app.cell
def __(Chunk, interactive_engine, mo, refined_node):
    # Verification: UAT-07 (Source Verification)

    # Get source chunks for the refined node
    source_chunks = list(interactive_engine.get_source_chunks(refined_node.id, limit=5))

    print(f"Found {len(source_chunks)} source chunks.")
    if len(source_chunks) > 0:
        print(f"Sample Chunk: {source_chunks[0].text[:50]}...")

    assert len(source_chunks) > 0
    assert isinstance(source_chunks[0], Chunk)

    mo.md("### 🎯 **UAT-07 Passed**: Traceability to source chunks confirmed.")
    return source_chunks


@app.cell
def __(db_path, mo):
    mo.md(
        f"""
        ## Part 5: Launching the GUI (Cycle 05)

        The automated verification is complete!

        To explore the tree visually:
        1. Open a terminal.
        2. Run: `uv run matome serve {db_path}`
        3. Open your browser to `http://localhost:5006`
        """
    )


@app.cell
def __(mo):
    mo.md("# 🎉 All Systems Go: Matome 2.0 is ready for Knowledge Installation.")
