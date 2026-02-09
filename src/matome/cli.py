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
) -> None:
    """
    Run the full summarization pipeline on a text file.
    """
    typer.echo(f"Starting Matome Pipeline for: {input_file}")

    # ensure output dir exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    # We can map CLI args to config
    # Note: Using env vars for secrets like API keys
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

    # Initialize components with progress bars where possible
    # Note: engines don't take tqdm bar directly, but we can wrap iterators if needed.
    # For now, just logging progress steps.

    typer.echo("Initializing engines...")
    chunker = JapaneseTokenChunker()
    embedder = EmbeddingService(config)
    clusterer = GMMClusterer()
    summarizer = SummarizationAgent(config)
    verifier = VerifierAgent(config) if config.verifier_enabled else None

    store_path = output_dir / "chunks.db"
    store = DiskChunkStore(db_path=store_path)

    engine = RaptorEngine(chunker, embedder, clusterer, summarizer, config)

    typer.echo("Running RAPTOR process (Chunk -> Embed -> Cluster -> Summarize)...")
    # We could add a spinner here
    with typer.progressbar(length=100, label="Processing") as progress:
        # RaptorEngine.run is blocking. We can't easily update progress bar unless we modify RaptorEngine to accept a callback.
        # Given constraints, we'll just run it and rely on logs for detailed progress if verbose.
        # Or we can just show a spinner.
        tree = engine.run(text, store=store)
        progress.update(100)

    typer.echo("Tree construction complete.")

    if verifier and config.verifier_enabled:
        typer.echo("Running Verification...")
        # Verify the root node or all summary nodes?
        # Typically we verify the summary against source.
        # For Raptor, maybe we verify the Root Summary against the raw text?
        # Or verify each summary node against its children.
        # The prompt says "Source Text".
        # Let's verify the Root Summary against the raw text (if fits context) or top chunks.
        # For this cycle, let's verify the root summary against the chunks.

        # We need to reconstruct source text for the root summary.
        # The root summary summarizes its children.
        # Getting the full text might be too large.
        # But we'll try verification on the Root Node.

        root_summary = tree.root_node.text
        # Naive approach: Verify against original text (might be too long).
        # Better: Verify against children text.

        # Let's verify the root node against its direct children text combined.
        # Retrieve children
        child_texts = []
        for idx in tree.root_node.children_indices:
            node = store.get_node(idx)
            if node:
                child_texts.append(node.text)

        source_text_for_verification = "\n\n".join(child_texts)

        # Truncate if too long?
        # VerificationAgent handles it via LLM limit usually, but we should be careful.

        result = verifier.verify(root_summary, source_text_for_verification)
        typer.echo(f"Verification Score: {result.score}")

        # Save verification result
        with (output_dir / "verification_result.json").open("w") as f:
            f.write(result.model_dump_json(indent=2))

    typer.echo("Exporting results...")

    # Markdown Export
    md_output = export_to_markdown(tree, store)
    (output_dir / "summary_all.md").write_text(md_output, encoding="utf-8")

    # Obsidian Canvas Export
    obs_exporter = ObsidianCanvasExporter(config)
    obs_exporter.export(tree, output_dir / "summary_kj.canvas", store)

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
    # This would require loading the tree from DB.
    # Currently DocumentTree is not persisted as a whole object, but nodes are.
    # We would need to reconstruct the tree.
    # RaptorEngine._finalize_tree does this but it needs current_level_ids.
    # If we persist tree metadata, we can reload.
    # For now, this might be a placeholder or we just dump what we can.

    typer.echo("Export from DB is not fully implemented in this cycle (requires tree persistence).")
    # Implementing minimal dump if needed.


if __name__ == "__main__":
    app()
