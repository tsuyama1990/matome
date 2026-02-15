# type: ignore
import logging
import sys
from pathlib import Path

# Ensure src is in path
sys.path.append(str(Path.cwd() / "src"))

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.utils.store import DiskChunkStore


def run_uat():
    print("Imports successful")

    # Setup Mock Environment
    store = DiskChunkStore(None)
    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(store=store, summarizer=None, config=config)

    print("Engine initialized")

    # Create Data
    c1 = Chunk(index=0, text="Alice has a cat.", start_char_idx=0, end_char_idx=15)
    c2 = Chunk(index=1, text="The cat is black.", start_char_idx=16, end_char_idx=32)

    s1 = SummaryNode(
        id="summary_1",
        text="Alice's pet details.",
        level=1,
        children_indices=[0, 1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.INFORMATION)
    )

    # Ingest Data
    store.add_chunks([c1, c2])
    store.add_summary(s1)

    print("Data ingested")

    # UAT Verification: Traceability
    try:
        sources = engine.get_source_chunks("summary_1")
        print(f"Found {len(sources)} source chunks")

        assert len(sources) == 2
        assert c1 in sources
        assert c2 in sources
        print("UAT PASSED: Traceability confirmed.")
    except AttributeError:
        print("UAT FAILED: get_source_chunks not implemented yet.")
        sys.exit(1)
    except Exception as e:
        print(f"UAT FAILED: {e}")
        raise

if __name__ == "__main__":
    run_uat()
