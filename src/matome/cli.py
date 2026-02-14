import logging
from pathlib import Path
from typing import Annotated

import panel as pn
import typer

from domain_models.config import ProcessingConfig
from domain_models.manifest import DocumentTree
from matome.agents.summarizer import SummarizationAgent
from matome.agents.verifier import VerifierAgent
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.engines.raptor import RaptorEngine
from matome.engines.token_chunker import JapaneseTokenChunker
from matome.exporters.markdown import stream_markdown
from matome.exporters.obsidian import ObsidianCanvasExporter
from matome.ui.canvas import MatomeCanvas
from matome.ui.view_model import InteractiveSession
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

# Initialize defaults once to use in help text
# We use defaults from config model directly in CLI definition
DEFAULT_CONFIG = ProcessingConfig.default()


def _handle_file_too_large(size: int) -> None:
    """Handle error when file is too large."""
    typer.echo(f"File too large: {size} bytes. Limit is 500MB.", err=True)
    raise typer.Exit(code=1)


def _initialize_components(config: ProcessingConfig) -> tuple[
    JapaneseTokenChunker,
    EmbeddingService,
    GMMClusterer,
    SummarizationAgent,
    VerifierAgent | None,
]:
    """Initialize all processing engines."""
    typer.echo("Initializing engines...")
    chunker = JapaneseTokenChunker()
    embedder = EmbeddingService(config)
    clusterer = GMMClusterer()
    summarizer = SummarizationAgent(config)
    verifier = VerifierAgent(config) if config.verifier_enabled else None
    return chunker, embedder, clusterer, summarizer, verifier


def _run_pipeline(
    text: str,
    store: DiskChunkStore,
    config: ProcessingConfig,
    components: tuple[
        JapaneseTokenChunker,
        EmbeddingService,
        GMMClusterer,
        SummarizationAgent,
        VerifierAgent | None,
    ],
) -> DocumentTree:
    """Run the RAPTOR pipeline."""
    chunker, embedder, clusterer, summarizer, _ = components
    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    typer.echo("Running RAPTOR process (Chunk -> Embed -> Cluster -> Summarize)...")
    try:
        # RaptorEngine.run handles store lifecycle internally if passed, but we want to keep it open
        # The caller (cli.run) has opened the store.
        # RaptorEngine.run uses store_ctx which respects open store.
        return engine.run(text, store=store)
    except Exception as e:
        typer.echo(f"Error during RAPTOR execution: {e}", err=True)
        logger.exception("RAPTOR execution failed.")
        raise typer.Exit(code=1) from e


def _verify_results(
    tree: DocumentTree,
    store: DiskChunkStore,
    verifier: VerifierAgent,
    output_dir: Path,
) -> None:
    """Run verification on the generated tree."""
    typer.echo("Running Verification...")
    try:
        root_summary = tree.root_node.text
        child_texts = []
        for idx in tree.root_node.children_indices:
            node = store.get_node(idx)
            if node:
                child_texts.append(node.text)

        source_text = "\n\n".join(child_texts)
        if len(source_text) > 50000:
            source_text = source_text[:50000] + "...(truncated)"

        result = verifier.verify(root_summary, source_text)
        typer.echo(f"Verification Score: {result.score}")

        with (output_dir / "verification_result.json").open("w") as f:
            f.write(result.model_dump_json(indent=2))

    except Exception as e:
        typer.echo(f"Verification failed: {e}", err=True)
        logger.exception("Verification failed.")


def _export_results(
    tree: DocumentTree,
    store: DiskChunkStore,
    config: ProcessingConfig,
    output_dir: Path,
) -> None:
    """Export results to various formats."""
    typer.echo("Exporting results...")
    try:
        # Stream markdown export to file
        with (output_dir / "summary_all.md").open("w", encoding="utf-8") as f:
            for line in stream_markdown(tree, store):
                f.write(line)

        obs_exporter = ObsidianCanvasExporter(config)
        obs_exporter.export(tree, output_dir / "summary_kj.canvas", store)
    except Exception as e:
        typer.echo(f"Export failed: {e}", err=True)
        logger.exception("Export failed.")


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
        str,
        typer.Option(
            "--model",
            "-m",
            help="Summarization model to use.",
        ),
    ] = DEFAULT_CONFIG.summarization_model,
    verifier_model: Annotated[
        str,
        typer.Option(
            "--verifier-model",
            "-v",
            help="Verification model to use.",
        ),
    ] = DEFAULT_CONFIG.verification_model,
    verify: Annotated[
        bool,
        typer.Option(
            "--verify/--no-verify",
            help="Enable/Disable verification.",
        ),
    ] = DEFAULT_CONFIG.verifier_enabled,
    max_tokens: Annotated[
        int, typer.Option(help="Max tokens per chunk.")
    ] = DEFAULT_CONFIG.max_tokens,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Processing mode: 'dikw' for Wisdom/Knowledge/Info, 'default' for standard summary.",
        ),
    ] = "dikw",
) -> None:
    """
    Run the full summarization pipeline on a text file.
    """
    typer.echo(f"Starting Matome Pipeline for: {input_file}")
    output_dir.mkdir(parents=True, exist_ok=True)

    config = ProcessingConfig(
        summarization_model=model,
        verification_model=verifier_model,
        verifier_enabled=verify,
        max_tokens=max_tokens,
    )

    if mode.lower() != "dikw":
        config = config.model_copy(update={"strategy_mapping": {}})
        typer.echo("Running in DEFAULT mode (Standard Summarization).")
    else:
        typer.echo("Running in DIKW mode (Wisdom/Knowledge/Information).")

    try:
        # Check file size before reading to prevent loading massive files into memory
        file_stats = input_file.stat()
        # 500MB Limit (just a safety net, though 100k-10M structures implies smaller text)
        if file_stats.st_size > 500 * 1024 * 1024:
            _handle_file_too_large(file_stats.st_size)

        text = input_file.read_text(encoding="utf-8")
    except Exception as e:
        typer.echo(f"Error reading file: {e}", err=True)
        raise typer.Exit(code=1) from e

    components = _initialize_components(config)
    chunker, embedder, clusterer, summarizer, verifier = components

    store_path = output_dir / "chunks.db"
    store = DiskChunkStore(db_path=store_path)

    with store as active_store:
        tree = _run_pipeline(text, active_store, config, components)
        typer.echo("Tree construction complete.")

        if verifier and config.verifier_enabled:
            _verify_results(tree, active_store, verifier, output_dir)

        _export_results(tree, active_store, config, output_dir)

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
    typer.echo("Export from DB is not fully implemented in this cycle.")


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
    port: Annotated[int, typer.Option("--port", "-p", help="Port to serve on.")] = DEFAULT_CONFIG.server_port,
) -> None:
    """
    Launch the interactive GUI.
    """
    # Initialize Panel extension
    pn.extension(sizing_mode="stretch_width")

    typer.echo(f"Starting Matome GUI on port {port}...")

    store = DiskChunkStore(db_path=store_path)

    try:
        config = ProcessingConfig()  # Default config for now
        # Read-only mode: summarizer=None
        engine = InteractiveRaptorEngine(store=store, summarizer=None, config=config)
        session = InteractiveSession(engine=engine)

        # Load initial tree
        session.load_tree()

        canvas = MatomeCanvas(session)

        # Serve
        pn.serve(canvas.view, port=port, show=False, title="Matome")  # type: ignore[no-untyped-call]
    except Exception as e:
        typer.echo(f"Error serving GUI: {e}", err=True)
        raise typer.Exit(code=1) from e
    finally:
        store.close()


if __name__ == "__main__":
    app()
