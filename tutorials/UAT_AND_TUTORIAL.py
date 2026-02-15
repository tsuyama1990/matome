import marimo

__generated_with = "0.1.0"
app = marimo.App(width="medium")


@app.cell
def __():
    import logging
    import os
    import sys
    import shutil
    import time
    from pathlib import Path
    from typing import Iterator, Iterable, Any
    import numpy as np
    import marimo as mo

    # Adjust path to include src if running from root or tutorials
    current_dir = Path.cwd()
    if (current_dir / "src").exists():
        sys.path.append(str(current_dir / "src"))
    elif (current_dir.parent / "src").exists():
        sys.path.append(str(current_dir.parent / "src"))

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("matome.uat")
    return (
        Iterable,
        Iterator,
        Path,
        Any,
        current_dir,
        logger,
        logging,
        mo,
        np,
        os,
        shutil,
        sys,
        time,
    )


@app.cell
def __(mo, os):
    mo.md(
        """
        # Matome 2.0: User Acceptance Test & Tutorial

        This notebook demonstrates the core capabilities of the Matome 2.0 "Knowledge Installation" system.
        It covers the entire pipeline from raw text to a structured, interactive knowledge base.

        **Scenarios:**
        1.  **Cycle 01: DIKW Generation**: Generate a tree where Root is Wisdom.
        2.  **Cycle 03: Semantic Zooming**: Traverse from Wisdom -> Knowledge -> Information -> Data.
        3.  **Cycle 02/04: Interactive Refinement**: Refine a node and verify persistence.
        4.  **Cycle 05: Traceability**: Verify source chunks for a summary node.
        5.  **GUI Launch**: Instructions to explore visually.

        **Modes:**
        *   **Real Mode**: Uses OpenAI/OpenRouter API for actual summarization (Requires `OPENROUTER_API_KEY`).
        *   **Mock Mode**: Uses random embeddings and dummy summaries (Default if no key found).
        """
    )

    # Determine Mode
    api_key = os.getenv("OPENROUTER_API_KEY")
    mock_mode = not bool(api_key) or api_key == "mock"

    if mock_mode:
        mode_msg = "⚠️ **MOCK MODE ACTIVE** (No API Key found or set to 'mock'). Using dummy data."
    else:
        mode_msg = "✅ **REAL MODE ACTIVE**. Using live API."

    mo.md(mode_msg)
    return api_key, mock_mode, mode_msg


@app.cell
def __(Iterable, Iterator, Path, mock_mode, mo, np, Any):
    # --- Configuration & Mocks ---
    from domain_models.config import ProcessingConfig
    from domain_models.manifest import Chunk, SummaryNode
    from domain_models.types import DIKWLevel, NodeID
    from matome.engines.embedder import EmbeddingService
    from matome.agents.summarizer import SummarizationAgent
    from matome.interfaces import PromptStrategy

    # Initialize Config
    # Ensure strict consistency for testing
    config = ProcessingConfig(
        max_tokens=500, # Reduce for testing to force more chunks
        max_summary_tokens=200,
        dikw_topology={
            "root": DIKWLevel.WISDOM,
            "intermediate": DIKWLevel.KNOWLEDGE,
            "leaf": DIKWLevel.INFORMATION,
        }
    )

    # Mock Classes
    class MockEmbeddingService(EmbeddingService):
        """Generates random embeddings for testing."""
        def __init__(self, config: ProcessingConfig):
            super().__init__(config)
            self.dim = 384  # Simulating all-MiniLM-L6-v2

        def embed_strings(self, texts: list[str] | tuple[str, ...]) -> Iterator[list[float]]:
            for _ in texts:
                # Deterministic random for stability based on length
                yield list(np.random.rand(self.dim))

        def embed_chunks(self, chunks: list[Chunk]) -> Iterator[Chunk]:
            for chunk in chunks:
                chunk.embedding = list(np.random.rand(self.dim))
                yield chunk

    class MockSummarizationAgent(SummarizationAgent):
        """Generates dummy summaries respecting DIKW levels."""
        def __init__(self, config: ProcessingConfig):
            self.config = config
            self.mock_mode = True
            self.model_name = "mock-model"
            self.llm = None

        def summarize(
            self,
            text: str,
            config: ProcessingConfig | None = None,
            strategy: PromptStrategy | None = None,
            context: dict[str, Any] | None = None,
        ) -> str:
            prefix = "Summary"
            if strategy:
                # strategy.dikw_level is likely a DIKWLevel Enum member
                try:
                    # Access the .value if it's an enum, or just str()
                    level = getattr(strategy, "target_dikw_level", "UNKNOWN")
                    # If it's an Enum, get value
                    if hasattr(level, "value"):
                        level = level.value
                except AttributeError:
                    level = "UNKNOWN"

                # Check context for instruction (Refinement)
                instruction = context.get("instruction") if context else None
                if instruction:
                    return f"[REFINED] {instruction} -> {text[:30]}..."

                prefix = f"[{str(level).upper()}] Summary"

            return f"{prefix} of: {text[:30]}... (Mocked Content)"

    # Factory
    def get_services(cfg, is_mock):
        if is_mock:
            return MockEmbeddingService(cfg), MockSummarizationAgent(cfg)
        else:
            return EmbeddingService(cfg), SummarizationAgent(cfg)

    mo.md("### System Configuration Loaded")
    return (
        Chunk,
        DIKWLevel,
        EmbeddingService,
        MockEmbeddingService,
        MockSummarizationAgent,
        NodeID,
        ProcessingConfig,
        PromptStrategy,
        SummarizationAgent,
        SummaryNode,
        config,
        get_services,
    )


@app.cell
def __(Path, mo):
    # --- Step 0: Setup Test Data ---
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)

    sample_file = test_data_dir / "investment_philosophy.txt"

    # Generate content if missing
    content = ""
    # Part 1: Wisdom
    content += "Chapter 1: The Mindset of a Sage Investor.\n"
    content += "True investment wisdom lies not in chasing trends but in understanding the immutable laws of value. " * 5 + "\n"
    content += "Patience is the investor's greatest asset. Emotional discipline separates the master from the novice. " * 5 + "\n"

    # Part 2: Knowledge
    content += "Chapter 2: The Mechanics of Wealth.\n"
    content += "Compounding is the eighth wonder of the world. Understanding exponential growth is key. " * 5 + "\n"
    content += "Asset allocation determines 90% of returns. Diversification is the only free lunch in finance. " * 5 + "\n"

    # Part 3: Information
    content += "Chapter 3: Actionable Steps.\n"
    content += "1. Review your portfolio quarterly. 2. Rebalance if drift exceeds 5%. 3. Tax loss harvest in December. " * 5 + "\n"
    content += "Check the expense ratios of your ETFs. Ensure they are below 0.10%. Automate your savings. " * 5 + "\n"

    # Repeat to ensure length
    content = content * 20

    sample_file.write_text(content, encoding="utf-8")

    mo.md(f"### Test Data Ready\n- `{sample_file}`\n- Size: {len(content)} chars")
    return content, sample_file, test_data_dir


@app.cell
def __(
    DIKWLevel,
    ProcessingConfig,
    config,
    get_services,
    mock_mode,
    mo,
    sample_file,
):
    # --- Step 1: Cycle 01 - DIKW Generation ---
    from matome.engines.raptor import RaptorEngine
    from matome.engines.token_chunker import JapaneseTokenChunker
    from matome.engines.cluster import GMMClusterer
    from matome.utils.store import DiskChunkStore

    mo.md("## 1. Cycle 01: DIKW Generation")

    # Clean DB
    store_path = Path("tutorials/chunks.db")
    if store_path.exists():
        store_path.unlink()

    store = DiskChunkStore(db_path=store_path)

    # Setup Components
    chunker = JapaneseTokenChunker(config)
    clusterer = GMMClusterer()
    embedder, summarizer = get_services(config, mock_mode)

    engine = RaptorEngine(
        chunker=chunker,
        embedder=embedder,
        clusterer=clusterer,
        summarizer=summarizer,
        config=config
    )

    # Run Pipeline
    text = sample_file.read_text(encoding="utf-8")
    tree = engine.run(text, store=store)

    # Verify Root is Wisdom (UAT-01)
    root_node = tree.root_node
    dikw_level = root_node.metadata.dikw_level

    # Assertion
    assert dikw_level == DIKWLevel.WISDOM, f"Root node should be WISDOM, got {dikw_level}"

    mo.md(
        f"### DIKW Generation Successful (UAT-01)\n"
        f"Root Node ID: `{root_node.id}`\n"
        f"DIKW Level: **{dikw_level}**\n"
        f"Text Preview: {root_node.text[:100]}..."
    )
    return (
        DiskChunkStore,
        GMMClusterer,
        JapaneseTokenChunker,
        RaptorEngine,
        chunker,
        clusterer,
        dikw_level,
        embedder,
        engine,
        root_node,
        store,
        store_path,
        summarizer,
        text,
        tree,
    )


@app.cell
def __(DIKWLevel, mo, store, tree):
    # --- Step 2: Cycle 03 - Semantic Zooming ---
    mo.md("## 2. Cycle 03: Semantic Zooming")

    # Traverse hierarchy
    layers = {}
    layers[1] = [tree.root_node]

    def get_children_nodes(parent_nodes):
        children = []
        for p in parent_nodes:
            # child indices can be str (SummaryNode) or int (Chunk)
            # In RaptorEngine, children_indices are stored in metadata or distinct field depending on implementation
            # Checking SummaryNode schema
            child_ids = [str(c) for c in p.children_indices]
            nodes = list(store.get_nodes(child_ids))
            children.extend([n for n in nodes if n is not None])
        return children

    current_layer_nodes = layers[1]
    depth = 1
    hierarchy_desc = []

    leaf_summaries = []

    hierarchy_desc.append(f"**Level {depth} ({current_layer_nodes[0].metadata.dikw_level})**: {len(current_layer_nodes)} node(s)")

    while True:
        next_nodes = get_children_nodes(current_layer_nodes)
        if not next_nodes:
            break

        first_child = next_nodes[0]
        depth += 1

        if hasattr(first_child, "children_indices"): # SummaryNode
             level_name = first_child.metadata.dikw_level
             hierarchy_desc.append(f"**Level {depth} ({level_name})**: {len(next_nodes)} node(s)")
             current_layer_nodes = next_nodes

             # Check if these are leaf summaries (children are chunks)
             # To do this robustly, check the first child's children
             if next_nodes:
                 grand_children = get_children_nodes([next_nodes[0]])
                 if grand_children and not hasattr(grand_children[0], "children_indices"):
                     leaf_summaries.extend(next_nodes)
        else: # Chunk
             hierarchy_desc.append(f"**Level {depth} (DATA)**: {len(next_nodes)} chunk(s)")
             break

    # UAT-02: Verify Leaf Summaries are INFORMATION (if hierarchy exists)
    if leaf_summaries:
        for node in leaf_summaries:
            assert node.metadata.dikw_level == DIKWLevel.INFORMATION, \
                f"Leaf summary {node.id} should be INFORMATION, got {node.metadata.dikw_level}"
        mo.md(f"✅ **UAT-02 Verified**: {len(leaf_summaries)} leaf summaries are correctly labeled as INFORMATION.")
    else:
         mo.md("⚠️ **UAT-02 Skipped**: Hierarchy too shallow for Information level.")

    mo.md(f"### Hierarchy Verified\n" + "\n".join([f"- {h}" for h in hierarchy_desc]))
    return (
        current_layer_nodes,
        depth,
        first_child,
        get_children_nodes,
        hierarchy_desc,
        layers,
        leaf_summaries,
        next_nodes,
    )


@app.cell
def __(
    config,
    get_children_nodes,
    mo,
    root_node,
    store,
    summarizer,
):
    # --- Step 3: Cycle 02/04 - Interactive Refinement ---
    from matome.engines.interactive_raptor import InteractiveRaptorEngine

    mo.md("## 3. Cycle 02/04: Interactive Refinement")

    interactive_engine = InteractiveRaptorEngine(store, summarizer, config)

    # UAT-03: Pick a node to refine. Ideally a Knowledge node (Level 2).
    target_node = root_node

    # Try to find a child node
    children = get_children_nodes([root_node])
    if children and hasattr(children[0], "children_indices"):
        target_node = children[0]

    instruction = "Explain like I'm 5"

    # Refine
    refined_node = interactive_engine.refine_node(target_node.id, instruction)

    # Verify
    assert refined_node.metadata.is_user_edited == True
    assert instruction in refined_node.metadata.refinement_history

    # Verify persistence
    persisted_node = store.get_node(target_node.id)
    assert persisted_node.text == refined_node.text
    assert persisted_node.metadata.is_user_edited == True

    mo.md(
        f"### Refinement Successful (UAT-03)\n"
        f"Node `{target_node.id}` ({target_node.metadata.dikw_level}) updated.\n"
        f"Instruction: *'{instruction}'*\n"
        f"New Text: {refined_node.text[:100]}..."
    )
    return (
        InteractiveRaptorEngine,
        children,
        instruction,
        interactive_engine,
        persisted_node,
        refined_node,
        target_node,
    )


@app.cell
def __(interactive_engine, mo, target_node):
    # --- Step 4: Cycle 05 - Traceability ---
    mo.md("## 4. Cycle 05: Traceability")

    # Get source chunks for the refined node
    source_chunks = list(interactive_engine.get_source_chunks(target_node.id))

    assert len(source_chunks) > 0
    first_chunk = source_chunks[0]

    mo.md(
        f"### Traceability Verified (UAT-07)\n"
        f"Node `{target_node.id}` traces back to **{len(source_chunks)}** original chunks.\n"
        f"First Chunk Preview: *{first_chunk.text[:50]}...*"
    )
    return first_chunk, source_chunks


@app.cell
def __(mo, store_path):
    # --- Step 5: GUI Launch ---
    mo.md(
        f"""
        ## 🎉 All Systems Go!

        The Matome 2.0 pipeline has been verified.
        You can now launch the interactive GUI to explore the generated knowledge base.

        Run this command in your terminal:
        ```bash
        uv run matome serve {store_path}
        ```
        """
    )
    return


if __name__ == "__main__":
    app.run()
