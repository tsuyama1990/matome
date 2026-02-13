import logging
from pathlib import Path
from typing import Annotated

import panel as pn
import typer

from domain_models.config import ProcessingConfig
from matome.agents.strategies import (
    BaseSummaryStrategy,
    InformationStrategy,
    KnowledgeStrategy,
    WisdomStrategy,
)
from matome.agents.summarizer import SummarizationAgent
from matome.agents.verifier import VerifierAgent
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.engines.raptor import RaptorEngine
from matome.engines.token_chunker import JapaneseTokenChunker
from matome.exporters.markdown import export_to_markdown
from matome.exporters.obsidian import ObsidianCanvasExporter
from matome.interfaces import PromptStrategy
from matome.ui.canvas import MatomeCanvas
from matome.ui.session import InteractiveSession
from matome.utils.store import DiskChunkStore

# Configure logging to stderr so it doesn't interfere with stdout output if needed
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="matome",
    help="Matome: Long Context Summarization System using RAPTOR and Japanese Semantic Chunking.",
    add_completion=False,
)


@app.command()
def run(
    input_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to the input text file (TXT).",
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory to save the results.",
            file_okay=False,
            dir_okay=True,
            writable=True,
        ),
    ] = Path("results"),
    model: Annotated[
        str, typer.Option("--model", "-m", help="Summarization model to use.")
    ] = "openai/gpt-4o-mini",
    verifier_model: Annotated[
        str, typer.Option("--verifier-model", "-v", help="Verification model to use.")
    ] = "openai/gpt-4o-mini",
    verify: Annotated[
        bool, typer.Option("--verify/--no-verify", help="Enable/Disable verification.")
    ] = True,
    max_tokens: Annotated[int, typer.Option(help="Max tokens per chunk.")] = 500,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Summarization mode: wisdom, knowledge, information, data (default).",
        ),
    ] = "data",
) -> None:
    """
    Run the full summarization pipeline on a text file.
    """
    typer.echo(f"Starting Matome Pipeline for: {input_file}")

    # ensure output dir exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    config = ProcessingConfig(
        summarization_model=model,
        verification_model=verifier_model,
        verifier_enabled=verify,
        max_tokens=max_tokens,
    )

    try:
        text = input_file.read_text(encoding="utf-8")
    except Exception as e:
        typer.echo(f"Error reading file: {e}", err=True)
        raise typer.Exit(code=1) from e

    typer.echo("Initializing engines...")
    chunker = JapaneseTokenChunker()
    embedder = EmbeddingService(config)
    clusterer = GMMClusterer()

    strategy = _select_strategy(mode)
    summarizer = SummarizationAgent(config, strategy=strategy)
    verifier = VerifierAgent(config) if config.verifier_enabled else None

    store_path = output_dir / "chunks.db"
    store = DiskChunkStore(db_path=store_path)

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    typer.echo("Running RAPTOR process (Chunk -> Embed -> Cluster -> Summarize)...")
    with typer.progressbar(length=100, label="Processing") as progress:
        tree = engine.run(text, store=store)
        progress.update(100)

    typer.echo("Tree construction complete.")

    if verifier and config.verifier_enabled:
        typer.echo("Running Verification...")
        root_summary = tree.root_node.text
        child_texts = []
        for idx in tree.root_node.children_indices:
            node = store.get_node(idx)
            if node:
                child_texts.append(node.text)

        source_text_for_verification = "\n\n".join(child_texts)

        # Basic truncation to avoid huge contexts
        if len(source_text_for_verification) > 100000:
            source_text_for_verification = source_text_for_verification[:100000]

        result = verifier.verify(root_summary, source_text_for_verification)
        typer.echo(f"Verification Score: {result.score}")

        with (output_dir / "verification_result.json").open("w") as f:
            f.write(result.model_dump_json(indent=2))

    typer.echo("Exporting results...")

    md_output = export_to_markdown(tree, store=store)
    (output_dir / "summary_all.md").write_text(md_output, encoding="utf-8")

    obs_exporter = ObsidianCanvasExporter(config)
    obs_exporter.export(tree, output_dir / "summary_kj.canvas", store=store)

    typer.echo(f"Done! Results saved in {output_dir}")


@app.command()
def export(
    store_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to the chunks.db file.",
        ),
    ],
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Directory to save the export.")
    ] = Path("export"),
    output_format: Annotated[
        str, typer.Option("--format", "-f", help="Format: markdown or canvas")
    ] = "markdown",
) -> None:
    """
    Export an existing database to a specific format.
    """
    typer.echo("Export from DB is not fully implemented in this cycle (requires tree persistence).")


@app.command()
def serve(
    store_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to the chunks.db file.",
        ),
    ],
    port: Annotated[int, typer.Option("--port", "-p", help="Port to serve on.")] = 5006,
    model: Annotated[
        str, typer.Option("--model", "-m", help="Summarization model for refinement.")
    ] = "openai/gpt-4o-mini",
) -> None:
    """
    Start the Matome Interactive GUI.
    """
    typer.echo(f"Starting Matome GUI on port {port}...")

    # Init Store
    store = DiskChunkStore(db_path=store_path)

    # Init Agent
    config = ProcessingConfig(summarization_model=model)
    # Strategy: For refinement, the engine dynamically wraps the strategy based on level.
    # So we can initialize with a default strategy here.
    agent = SummarizationAgent(config, strategy=BaseSummaryStrategy())

    # Init Engine
    engine = InteractiveRaptorEngine(store=store, agent=agent)

    def create_app() -> pn.template.BaseTemplate:
        """Create a new session-isolated app instance."""
        # Init Session (ViewModel) for this user
        session = InteractiveSession(engine=engine)
        # Init Canvas (View)
        canvas = MatomeCanvas(session=session)
        return canvas.layout

    # Serve
    pn.serve(create_app, port=port, show=False)  # type: ignore[no-untyped-call]


def _select_strategy(mode: str) -> PromptStrategy:
    """Select summarization strategy based on mode."""
    if mode == "wisdom":
        typer.echo("Mode: WISDOM (L1)")
        return WisdomStrategy()
    if mode == "knowledge":
        typer.echo("Mode: KNOWLEDGE (L2)")
        return KnowledgeStrategy()
    if mode == "information":
        typer.echo("Mode: INFORMATION (L3)")
        return InformationStrategy()

    typer.echo("Mode: DATA/DEFAULT (Chain of Density)")
    return BaseSummaryStrategy()


if __name__ == "__main__":
    app()
