import logging
from pathlib import Path
from typing import Annotated

import typer

from domain_models.config import ProcessingConfig
from matome.agents.summarizer import SummarizationAgent
from matome.agents.verifier import VerifierAgent
from matome.engines.cluster import GMMClusterer
from matome.engines.embedder import EmbeddingService
from matome.engines.raptor import RaptorEngine
from matome.engines.token_chunker import JapaneseTokenChunker
from matome.exporters.markdown import export_to_markdown
from matome.exporters.obsidian import ObsidianCanvasExporter
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
            help="Processing mode: 'dikw' for Wisdom/Knowledge/Info, 'default' for standard summary.",
        ),
    ] = "dikw",
) -> None:
    """
    Run the full summarization pipeline on a text file.
    """
    typer.echo(f"Starting Matome Pipeline for: {input_file}")

    # ensure output dir exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    # We can map CLI args to config
    config = ProcessingConfig(
        summarization_model=model,
        verification_model=verifier_model,
        verifier_enabled=verify,
        max_tokens=max_tokens,
    )

    # Handle mode
    if mode.lower() != "dikw":
        # Clear strategy mapping to disable DIKW logic
        # Since config is frozen, we must create a new one or rely on object mutation (bad) or dict copying
        # ProcessingConfig is frozen.
        # We need to create a new config with empty strategy_mapping.
        config = config.model_copy(update={"strategy_mapping": {}})
        typer.echo("Running in DEFAULT mode (Standard Summarization).")
    else:
        typer.echo("Running in DIKW mode (Wisdom/Knowledge/Information).")

    try:
        text = input_file.read_text(encoding="utf-8")
    except Exception as e:
        typer.echo(f"Error reading file: {e}", err=True)
        raise typer.Exit(code=1) from e

    # Initialize components
    typer.echo("Initializing engines...")
    chunker = JapaneseTokenChunker()
    embedder = EmbeddingService(config)
    clusterer = GMMClusterer()
    summarizer = SummarizationAgent(config)
    verifier = VerifierAgent(config) if config.verifier_enabled else None

    store_path = output_dir / "chunks.db"
    # Ensure previous DB is cleared or we append?
    # Usually we want fresh start for a run command on same output dir?
    # If store_path exists, DiskChunkStore might open existing.
    # For now, we assume user manages output dir.
    store = DiskChunkStore(db_path=store_path)

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    typer.echo("Running RAPTOR process (Chunk -> Embed -> Cluster -> Summarize)...")

    # Use a persistent store connection for the whole run
    # Wait, RaptorEngine.run accepts store.
    # And DiskChunkStore is a context manager.
    # But RaptorEngine.run calls _process_recursion which passes store around.
    # store is not entered here.
    # RaptorEngine.run does: `with store_ctx as active_store:`
    # If we pass `store`, it uses `nullcontext(store)`.
    # So we should open `store` here.

    try:
        with store as active_store:
            tree = engine.run(text, store=active_store)
    except Exception as e:
        typer.echo(f"Error during RAPTOR execution: {e}", err=True)
        logger.exception("RAPTOR execution failed.")
        raise typer.Exit(code=1) from e

    typer.echo("Tree construction complete.")

    if verifier and config.verifier_enabled:
        typer.echo("Running Verification...")
        try:
            root_summary = tree.root_node.text
            # Verify against children text.
            child_texts = []
            for idx in tree.root_node.children_indices:
                node = store.get_node(idx)
                if node:
                    child_texts.append(node.text)

            source_text_for_verification = "\n\n".join(child_texts)

            # Limit verification text length to avoid context window issues
            # Rough char limit (e.g. 50k chars)
            if len(source_text_for_verification) > 50000:
                 source_text_for_verification = source_text_for_verification[:50000] + "...(truncated)"

            result = verifier.verify(root_summary, source_text_for_verification)
            typer.echo(f"Verification Score: {result.score}")

            # Save verification result
            with (output_dir / "verification_result.json").open("w") as f:
                f.write(result.model_dump_json(indent=2))

        except Exception as e:
            typer.echo(f"Verification failed: {e}", err=True)
            # Don't fail the whole run
            logger.exception("Verification failed.")

    typer.echo("Exporting results...")

    try:
        # Markdown Export
        # Markdown exporter needs to traverse tree.
        # It needs the store to fetch nodes.
        # Tree no longer has all_nodes.
        md_output = export_to_markdown(tree, store)
        (output_dir / "summary_all.md").write_text(md_output, encoding="utf-8")

        # Obsidian Canvas Export
        obs_exporter = ObsidianCanvasExporter(config)
        obs_exporter.export(tree, output_dir / "summary_kj.canvas", store)
    except Exception as e:
        typer.echo(f"Export failed: {e}", err=True)
        logger.exception("Export failed.")

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


if __name__ == "__main__":
    app()
