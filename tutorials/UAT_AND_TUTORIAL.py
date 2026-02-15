import marimo

__generated_with = "0.9.14"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo
    import os
    import sys
    import logging
    from pathlib import Path

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
    return Path, logger, logging, mo, os, sys


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
def __(mo):
    mo.md("## Part 1: The 'Grok' Moment (Cycle 01)")
    return


@app.cell
def __(mock_mode):
    from domain_models.config import ProcessingConfig
    from domain_models.types import DIKWLevel
    from domain_models.manifest import SummaryNode
    from matome.engines.raptor import RaptorEngine
    from matome.engines.token_chunker import JapaneseTokenChunker
    from matome.engines.embedder import EmbeddingService
    from matome.engines.cluster import GMMClusterer
    from matome.agents.summarizer import SummarizationAgent
    from matome.utils.store import DiskChunkStore

    # 1. Configuration
    config = ProcessingConfig(
        max_input_length=100000,
        max_summary_tokens=200,  # Short summaries for UAT
        clustering_algorithm="gmm", # Explicitly set
        # If in mock mode, we can reduce some heavy lifting if needed, but the structure remains
    )

    # 2. Dependency Injection
    # We explicitly initialize all components as per the architecture
    chunker = JapaneseTokenChunker(config)
    embedder = EmbeddingService(config)
    clusterer = GMMClusterer()
    summarizer = SummarizationAgent(config)

    # 3. Initialize Engine
    # RaptorEngine needs all these injected
    raptor = RaptorEngine(
        chunker=chunker,
        embedder=embedder,
        clusterer=clusterer,
        summarizer=summarizer,
        config=config,
    )

    print("✅ RaptorEngine Initialized")
    return (
        DIKWLevel,
        DiskChunkStore,
        EmbeddingService,
        GMMClusterer,
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
def __(DiskChunkStore, Path, config, mo, raptor):
    # Sample Text (Investment Philosophy - roughly 20 chunks worth for a real run, but we keep it smaller for UAT speed if Mock)
    # To trigger clustering, we need enough chunks.
    # Let's generate synthetic text if we are in mock mode or just a repeated string.

    base_text = """
    Value investing is an investment paradigm that involves buying securities that appear underpriced by some form of fundamental analysis.
    All forms of value investing derive from the philosophy of investment taught by Benjamin Graham and David Dodd at Columbia Business School in 1928.

    The concept of "margin of safety" is the principle of buying a security at a significant discount to its intrinsic value, which is thought to provide not only high-return opportunities but also to minimize the downside risk of an investment.
    Warren Buffett, a student of Graham, is a notable proponent of this strategy.

    Contrarian investing is an investment style in which investors purposefully go against prevailing market trends by selling when others are buying, and buying when most investors are selling.
    A contrarian investor believes that the people who say the market is going up do so only when they are fully invested and have no further purchasing power.
    """

    # Repeat to ensure we get enough chunks for at least one level of clustering
    # Each chunk is ~100 tokens. We want > 5 chunks to be safe for GMM.
    # Text length needed ~ 500-1000 tokens.

    full_text = (base_text + "\n\n") * 20

    print(f"Input Text Length: {len(full_text)} chars")

    # Run RAPTOR

    # Use a persistent file for UAT to inspect later, or temp if preferred.
    # Let's use a local file for the tutorial aspect.
    db_path = Path("tutorials/chunks.db")
    if db_path.exists():
        db_path.unlink() # Start fresh

    store = DiskChunkStore(db_path)

    print("🚀 Running RAPTOR Engine... (This may take a moment)")
    tree = raptor.run(full_text, store=store)

    print("✅ Tree Generation Complete.")
    print(f"Root Node ID: {tree.root_node.id}")
    print(f"Tree Depth: {tree.metadata.get('levels')}")

    return base_text, db_path, full_text, store, tree


@app.cell
def __(DIKWLevel, mo, tree):
    # Verification: UAT-01 (Wisdom Generation)
    root = tree.root_node

    # In Mock mode, levels might not be perfectly aligned if clustering was skipped or trivial,
    # but the logic should hold that the Root is the highest level.
    # The default Raptor strategy sets the top level to Wisdom.

    print(f"Root Text: {root.text[:100]}...")
    print(f"Root Level: {root.metadata.dikw_level}")

    assert root.metadata.dikw_level == DIKWLevel.WISDOM or root.metadata.dikw_level == "wisdom", \
        f"Expected Wisdom, got {root.metadata.dikw_level}"

    mo.md(f"### 🎯 **UAT-01 Passed**: Root node is verified as **{root.metadata.dikw_level}**.")
    return root


@app.cell
def __(mo):
    mo.md("## Part 2: Semantic Zooming (Cycle 03)")
    return


@app.cell
def __(config, store, summarizer):
    from matome.engines.interactive_raptor import InteractiveRaptorEngine

    # Initialize Interactive Engine
    interactive_engine = InteractiveRaptorEngine(
        store=store,
        summarizer=summarizer,
        config=config
    )

    print("✅ Interactive Engine Initialized")
    return InteractiveRaptorEngine, interactive_engine


@app.cell
def __(SummaryNode, interactive_engine, mo, root):
    # Traverse children
    children = list(interactive_engine.get_children(root))

    print(f"Root has {len(children)} children.")

    if len(children) > 0:
        first_child = children[0]
        # Check if first_child is a SummaryNode or Chunk
        level_info = "Chunk"

        if isinstance(first_child, SummaryNode):
            level_info = first_child.metadata.dikw_level

        print(f"First Child Level: {level_info}")

    # Verification: Hierarchy exists
    # If the text was small, the root might have chunks as children.
    assert len(children) > 0, "Root should have children"

    mo.md(f"### 🎯 **Tree Traversal Verified**: Root expands to {len(children)} nodes.")
    return children, first_child


@app.cell
def __(mo):
    mo.md("## Part 3: Interactive Refinement (Cycle 02 & 04)")
    return


@app.cell
def __(SummaryNode, children, interactive_engine, mo):
    # Select a node to refine (Knowledge or Information)
    # We pick the first child of the root (likely Knowledge)
    target_node = children[0]

    node_to_refine = None
    if isinstance(target_node, SummaryNode):
        node_to_refine = target_node
    else:
        # If root children are chunks, we can't refine them via this engine easily (it expects SummaryNode children)
        # Actually refine_node expects a SummaryNode ID.
        # If the tree is shallow (Root -> Chunks), we can only refine Root.
        print("Tree is shallow. Refining Root Node instead.")
        node_to_refine = interactive_engine.get_root_node()

    print(f"Refining Node: {node_to_refine.id}")
    print(f"Original Text: {node_to_refine.text[:50]}...")

    # Action: Refine
    instruction = "Explain this like I'm 5 years old."
    refined_node = interactive_engine.refine_node(node_to_refine.id, instruction)

    print(f"Refined Text: {refined_node.text[:50]}...")
    print(f"User Edited: {refined_node.metadata.is_user_edited}")

    # Verification: UAT-03 (Single Refinement)
    assert refined_node.metadata.is_user_edited is True
    assert instruction in refined_node.metadata.refinement_history

    mo.md("### 🎯 **UAT-03 Passed**: Node successfully refined and persisted.")
    return instruction, node_to_refine, refined_node, target_node


@app.cell
def __(mo):
    mo.md("## Part 4: Traceability (Cycle 05)")
    return


@app.cell
def __(interactive_engine, mo, node_to_refine):
    # Action: Get Source Chunks
    # We use the node we just refined
    source_chunks = list(interactive_engine.get_source_chunks(node_to_refine.id, limit=5))

    print(f"Found {len(source_chunks)} source chunks.")
    if len(source_chunks) > 0:
        print(f"Sample Chunk: {source_chunks[0].text[:50]}...")

    # Verification: UAT-07 (Source Verification)
    assert len(source_chunks) > 0
    assert hasattr(source_chunks[0], 'text')

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
    return


@app.cell
def __(mo):
    mo.md("# 🎉 All Systems Go: Matome 2.0 is ready for Knowledge Installation.")
    return
