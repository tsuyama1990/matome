
__generated_with = "0.19.11"

# %%
import logging
import os
import sys
from pathlib import Path
import random
import shutil
import time
from typing import Iterator, Iterable

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

# %%
mo.md(
    """
    # Matome 2.0: User Acceptance Test & Tutorial

    This notebook demonstrates the core capabilities of the Matome 2.0 "Knowledge Installation" system.
    It covers the entire pipeline from raw text to a structured, interactive knowledge base.

    **Scenarios:**
    1.  **Quickstart**: Text Ingestion & Chunking (The Basics)
    2.  **Clustering**: Semantic Embedding & Grouping (The Engine)
    3.  **Raptor Pipeline**: Recursive Summarization (The "Aha!" Moment)
    4.  **Visualization**: Obsidian Canvas Export (The Output)

    **Modes:**
    *   **Real Mode**: Uses OpenAI/OpenRouter API for actual summarization (Requires `OPENROUTER_API_KEY`).
    *   **Mock Mode**: Uses random embeddings and dummy summaries (Default if no key found).
    """
)

# Determine Mode
api_key = os.getenv("OPENROUTER_API_KEY")
mock_mode = not bool(api_key)

if mock_mode:
    mode_msg = "⚠️ **MOCK MODE ACTIVE** (No API Key found). Using dummy data."
else:
    mode_msg = "✅ **REAL MODE ACTIVE**. Using live API."

mo.md(mode_msg)

# %%
# --- Configuration & Mocks ---
from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk
from matome.engines.embedder import EmbeddingService
from matome.agents.summarizer import SummarizationAgent
from matome.interfaces import PromptStrategy

# Initialize Config
config = ProcessingConfig()

# Mock Classes
class MockEmbeddingService(EmbeddingService):
    """Generates random embeddings for testing."""
    def __init__(self, config: ProcessingConfig):
        super().__init__(config)
        self.dim = 384  # Simulating all-MiniLM-L6-v2

    def embed_strings(self, texts: list[str] | tuple[str, ...]) -> Iterator[list[float]]:
        for _ in texts:
            # Deterministic random for stability
            yield list(np.random.rand(self.dim))

    def embed_chunks(self, chunks: list[Chunk]) -> Iterator[Chunk]:
        for chunk in chunks:
            chunk.embedding = list(np.random.rand(self.dim))
            yield chunk

class MockSummarizationAgent(SummarizationAgent):
    """Generates dummy summaries."""
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
        context: dict | None = None,
    ) -> str:
        prefix = "Summary"
        if strategy:
            # strategy.dikw_level is an Enum
            try:
                level = strategy.dikw_level.value
            except AttributeError:
                level = "UNKNOWN"
            prefix = f"[{str(level).upper()}] Summary"
        return f"{prefix} of: {text[:30]}... (Mocked Content)"

# Factory
def get_services(cfg, is_mock):
    if is_mock:
        return MockEmbeddingService(cfg), MockSummarizationAgent(cfg)
    else:
        return EmbeddingService(cfg), SummarizationAgent(cfg)

mo.md("### System Configuration Loaded")

# %%
# --- Step 0: Setup Test Data ---
test_data_dir = Path("test_data")
test_data_dir.mkdir(exist_ok=True)

sample_file = test_data_dir / "sample.txt"
if not sample_file.exists():
    sample_file.write_text(
        "Matome 2.0 is a system for knowledge installation. "
        "It uses recursive summarization to build a tree of knowledge. "
        "This allows users to zoom from high-level wisdom to low-level data. "
        "The system is built on Python and uses modern libraries like Pydantic and LangChain. "
        "It supports both batch processing and interactive refinement. " * 5,
        encoding="utf-8"
    )

target_file = test_data_dir / "エミン流「会社四季報」最強の読み方.txt"
if not target_file.exists():
    target_file.write_text(
        "会社四季報は、日本の全上場企業のデータが網羅された書籍です。\n"
        "エミン・ユルマズ氏は、四季報を「お宝の山」と呼びます。\n"
        "彼の読み方は、単なる数字の確認にとどまりません。\n"
        "業績の変化、株主構成、そして企業のコメント欄を入念にチェックします。\n"
        "特に「ニコちゃんマーク」の変化に注目することで、成長株を早期に発見できるのです。\n" * 20,
        encoding="utf-8"
    )

mo.md(f"### Test Data Ready\n- `{sample_file}`\n- `{target_file}`")

# %%
# --- Step 1: Quickstart (Chunking) ---
from matome.engines.token_chunker import JapaneseTokenChunker

mo.md("## 1. Quickstart: Text Chunking")

# Load text
quickstart_text = sample_file.read_text(encoding="utf-8")

# Initialize Chunker
quickstart_chunker = JapaneseTokenChunker(config)

# Execute Chunking
quickstart_chunks = list(quickstart_chunker.split_text(quickstart_text, config))

# Visualize
chunk_preview = "\n".join([f"- **Chunk {c.index}**: {c.text[:50]}..." for c in quickstart_chunks[:5]])

mo.md(f"### Chunking Results\nGenerated **{len(quickstart_chunks)}** chunks.\n\n{chunk_preview}")

# %%
# --- Step 2: Clustering Deep Dive ---
from matome.engines.cluster import GMMClusterer

mo.md("## 2. Clustering Deep Dive")

# Setup
clustering_embedder, _ = get_services(config, mock_mode)
clustering_chunker = JapaneseTokenChunker(config)
clustering_clusterer = GMMClusterer()

# Process
text_cluster = sample_file.read_text(encoding="utf-8")
chunks_cluster = list(clustering_chunker.split_text(text_cluster, config))

# Embed & Cluster
embedded_chunks_iter = clustering_embedder.embed_chunks(chunks_cluster)

# Manually collect for the clusterer input
embeddings_input = []
for chunk in embedded_chunks_iter:
    if chunk.embedding:
        embeddings_input.append((str(chunk.index), chunk.embedding))

# Run Clustering
# Create a config suitable for small data (force fewer clusters)
cluster_config = ProcessingConfig(n_clusters=2, write_batch_size=10)

clustering_clusters = clustering_clusterer.cluster_nodes(embeddings_input, cluster_config)

cluster_info = "\n".join([f"- **Cluster {c.id}**: {len(c.node_indices)} nodes" for c in clustering_clusters])

mo.md(f"### Clustering Results\nGenerated **{len(clustering_clusters)}** clusters.\n\n{cluster_info}")

# %%
# --- Step 3: Full Raptor Pipeline ---
from matome.engines.raptor import RaptorEngine

mo.md("## 3. Full Raptor Pipeline (The 'Aha!' Moment)")

# Setup Components
chunker_raptor = JapaneseTokenChunker(config)
clusterer_raptor = GMMClusterer()
embedder_raptor, summarizer_raptor = get_services(config, mock_mode)

raptor_engine = RaptorEngine(
    chunker=chunker_raptor,
    embedder=embedder_raptor,
    clusterer=clusterer_raptor,
    summarizer=summarizer_raptor,
    config=config
)

# Run Pipeline
raptor_target_text = target_file.read_text(encoding="utf-8")
# Using default ephemeral store logic here for demonstration,
# but typically one would provide a store.
# We will do a full run with store in the next step/cell to enable visualization.

# For now, let's run it to verify the pipeline works in memory/temp.
raptor_tree = raptor_engine.run(raptor_target_text)

summary_content = f"# Summary Tree\n\nRoot: {raptor_tree.root_node.text}\n"

output_md = Path("summary_all.md")
output_md.write_text(summary_content, encoding="utf-8")

mo.md(
    f"### Pipeline Complete\n"
    f"Generated Tree with Root Level: **{raptor_tree.root_node.level}**\n"
    f"Output saved to `{output_md}`"
)

# %%
# --- Step 4: Visualization (Obsidian Canvas) ---
from matome.exporters.obsidian import ObsidianCanvasExporter
from matome.utils.store import DiskChunkStore

mo.md("## 4. Visualization (Obsidian Canvas)")

# Re-run for export with persistent store
store_path = Path("tutorials/chunks.db")
if store_path.exists():
    store_path.unlink() # Clean start

store = DiskChunkStore(db_path=store_path)

# Setup again
chunker_r = JapaneseTokenChunker(config)
clusterer_r = GMMClusterer()
embedder_r, summarizer_r = get_services(config, mock_mode)

engine_r = RaptorEngine(
    chunker=chunker_r,
    embedder=embedder_r,
    clusterer=clusterer_r,
    summarizer=summarizer_r,
    config=config
)

# Run with store
tree_r = engine_r.run(raptor_target_text, store=store)

# Export Canvas
exporter = ObsidianCanvasExporter(config)
output_canvas = Path("summary_kj.canvas")
exporter.export(tree_r, output_canvas, store)

mo.md(
    f"### Canvas Exported\n"
    f"File saved to: `{output_canvas}`\n"
    f"Database: `{store_path}`\n\n"
    f"**Next Step**: Open `{output_canvas}` in Obsidian to visualize!"
)
