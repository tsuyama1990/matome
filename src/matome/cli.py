import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, NoReturn

import panel as pn
import typer

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, DocumentTree, SummaryNode
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


def _fail_with_error(message: str) -> NoReturn:
    """Centralized error handling: Log error and exit with code 1."""
    typer.echo(message, err=True)
    logger.error(message)
    raise typer.Exit(code=1)


def _handle_file_too_large(size: int, limit: int) -> None:
    """Handle error when file is too large."""
    _fail_with_error(
        f"File too large: {size} bytes. Limit is {limit / (1024*1024):.2f}MB."
    )


def _validate_output_dir(output_dir: Path) -> None:
    """
    Validate output directory to prevent path traversal or unsafe locations.
    Enforces that the path must be relative to the current working directory
    and resolves symbolic links to ensure safety.
    """
    try:
        # Resolve path to handle '..' and absolute paths
        # strict=False because the directory might not exist yet
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()

        # Security check: Ensure path is relative to CWD to prevent writing to arbitrary system locations
        if not resolved.is_relative_to(cwd):
             _fail_with_error(f"Path must be within current working directory ({cwd})")

        # Check for symbolic link attacks
        # We check if the directory itself or any of its parents (up to CWD) are symlinks.
        # We traverse up until we hit the root or CWD or the path doesn't exist.

        check_path = output_dir
        while check_path != Path(check_path.anchor): # Stop at root
             if check_path.exists() and check_path.is_symlink():
                 _fail_with_error(f"Path component '{check_path.name}' is a symbolic link. Symlinks are not allowed for security.")

             if check_path == cwd:
                 break

             check_path = check_path.parent

        # Also double check resolved path is a directory if it exists
        if resolved.exists() and not resolved.is_dir():
             _fail_with_error(f"Path {output_dir} exists and is not a directory.")

    except Exception as e:
        _fail_with_error(f"Invalid output directory: {e!s}")


def _stream_file_content(path: Path, chunk_size: int = DEFAULT_CONFIG.io_buffer_size) -> Iterator[str]:
    """
    Stream file content chunk by chunk to avoid loading into memory.
    Yields decoded text chunks.
    """
    try:
        with path.open("r", encoding="utf-8", buffering=chunk_size) as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except UnicodeDecodeError as e:
        _fail_with_error(f"File encoding error: {e}. Please ensure the file is valid UTF-8.")
    except Exception as e:
        _fail_with_error(f"Error reading file stream: {e}")


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
    text_stream: Iterator[str],
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
        # Pass the stream generator directly
        return engine.run(text_stream, store=store)
    except Exception as e:
        logger.exception("RAPTOR execution failed.")
        _fail_with_error(f"Error during RAPTOR execution: {e}")


def _verify_results(
    tree: DocumentTree,
    store: DiskChunkStore,
    verifier: VerifierAgent,
    config: ProcessingConfig,
    output_dir: Path,
) -> None:
    """Run verification on the generated tree."""
    typer.echo("Running Verification...")
    try:
        # Narrow type for mypy
        if isinstance(tree.root_node, (SummaryNode, Chunk)):
             root_summary = tree.root_node.text

             child_texts = []
             # root_node could be Chunk which has no children_indices or SummaryNode which does
             # The loop only makes sense if it's a SummaryNode
             if isinstance(tree.root_node, SummaryNode):
                 for idx in tree.root_node.children_indices:
                     node = store.get_node(idx)
                     if node:
                         child_texts.append(node.text)
             elif isinstance(tree.root_node, Chunk):
                 # If root is a chunk, verification source is the chunk itself?
                 # Or we verify summary against source. But root IS source if it's a chunk.
                 # Let's just use the chunk text itself as source.
                 child_texts.append(tree.root_node.text)

             source_text = "\n\n".join(child_texts)
             if len(source_text) > config.verification_context_length:
                 source_text = source_text[:config.verification_context_length] + "...(truncated)"

             result = verifier.verify(root_summary, source_text)
             typer.echo(f"Verification Score: {result.score}")

             with (output_dir / "verification_result.json").open("w") as f:
                 f.write(result.model_dump_json(indent=2))
        else:
             typer.echo("Root node is empty, skipping verification.")

    except Exception as e:
        logger.exception("Verification failed.")
        typer.echo(f"Verification failed: {e}", err=True)


def _export_results(
    tree: DocumentTree,
    store: DiskChunkStore,
    config: ProcessingConfig,
    output_dir: Path,
) -> None:
    """Export results to various formats."""
    typer.echo("Exporting results...")
    try:
        # Stream markdown export to file with buffering
        markdown_path = output_dir / "summary_all.md"
        with markdown_path.open("w", encoding="utf-8", buffering=config.io_buffer_size) as f:
            for line in stream_markdown(tree, store):
                f.write(line)

        obs_exporter = ObsidianCanvasExporter(config)
        obs_exporter.export(tree, output_dir / "summary_kj.canvas", store)
    except Exception as e:
        logger.exception("Export failed.")
        typer.echo(f"Export failed: {e}", err=True)


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

    # Validate output dir safety
    _validate_output_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = ProcessingConfig(
        summarization_model=model,
        verification_model=verifier_model,
        verifier_enabled=verify,
        max_tokens=max_tokens,
    )

    if mode.lower() != "dikw":
        # If not DIKW, reset strategy mapping
        config = config.model_copy(update={"strategy_mapping": {}})
        typer.echo("Running in DEFAULT mode (Standard Summarization).")
    else:
        typer.echo("Running in DIKW mode (Wisdom/Knowledge/Information).")

    # Check file size before processing
    try:
        file_stats = input_file.stat()
        if file_stats.st_size > config.max_file_size_bytes:
            _handle_file_too_large(file_stats.st_size, config.max_file_size_bytes)
    except OSError as e:
        _fail_with_error(f"Error accessing file: {e}")

    # Create stream generator using config buffer size
    text_stream = _stream_file_content(input_file, chunk_size=config.io_buffer_size)

    components = _initialize_components(config)
    chunker, embedder, clusterer, summarizer, verifier = components

    store_path = output_dir / "chunks.db"

    # Use context manager for store to ensure cleanup
    # Configure store with batch sizes from config
    with DiskChunkStore(
        db_path=store_path,
        write_batch_size=config.store_write_batch_size,
        read_batch_size=config.store_read_batch_size
    ) as active_store:
        tree = _run_pipeline(text_stream, active_store, config, components)
        typer.echo("Tree construction complete.")

        if verifier and config.verifier_enabled:
            _verify_results(tree, active_store, verifier, config, output_dir)

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
    typer.echo("WARNING: The GUI server is not authenticated. It is bound to localhost (127.0.0.1) for security.")

    # Use context manager to ensure store is closed properly upon exit (e.g. Ctrl+C)
    try:
        with DiskChunkStore(db_path=store_path) as store:
            config = ProcessingConfig()  # Default config for now

            # Initialize SummarizationAgent for interactive refinement
            # Note: Requires OPENROUTER_API_KEY environment variable
            summarizer = SummarizationAgent(config)

            engine = InteractiveRaptorEngine(store=store, summarizer=summarizer, config=config)
            session = InteractiveSession(engine=engine)

            # Load initial tree
            session.load_tree()

            canvas = MatomeCanvas(session)

            # Serve (blocks until stopped)
            # Bind to 127.0.0.1 to prevent external access
            pn.serve(canvas.view, port=port, address="127.0.0.1", show=False, title="Matome")  # type: ignore[no-untyped-call]

    except Exception as e:
        logger.exception("Error serving GUI")
        _fail_with_error(f"Error serving GUI: {e}")


if __name__ == "__main__":
    app()
