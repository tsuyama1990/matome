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


def run_uat() -> None:
    logger = logging.getLogger("UAT")
    logging.basicConfig(level=logging.INFO)

    logger.info("Imports successful")

    # Setup Mock Environment
    store = DiskChunkStore(None)
    config = ProcessingConfig()
    engine = InteractiveRaptorEngine(store=store, summarizer=None, config=config)

    logger.info("Engine initialized")

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

    logger.info("Data ingested")

    # UAT Verification: Traceability
    try:
        # Convert iterator to list for assertion
        sources = list(engine.get_source_chunks("summary_1"))
        logger.info(f"Found {len(sources)} source chunks")

        _verify_sources(sources, [c1, c2])

        logger.info("UAT PASSED: Traceability confirmed.")
    except AttributeError:
        logger.exception("UAT FAILED: get_source_chunks not implemented yet.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"UAT FAILED: {e}")
        raise

def _verify_sources(sources: list[Chunk], expected: list[Chunk]) -> None:
    if len(sources) != len(expected):
        msg = f"Expected {len(expected)} sources, got {len(sources)}"
        raise RuntimeError(msg)

    for chunk in expected:
        if chunk not in sources:
            msg = f"Chunk {chunk.index} missing from sources"
            raise RuntimeError(msg)

if __name__ == "__main__":
    run_uat()
