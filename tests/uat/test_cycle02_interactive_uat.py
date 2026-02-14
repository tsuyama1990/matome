import threading
import time
from collections.abc import Iterator
from unittest.mock import MagicMock

from domain_models.config import ProcessingConfig
from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.utils.store import DiskChunkStore


def chunk_generator(start_index: int, count: int) -> Iterator[Chunk]:
    """Generator for chunks."""
    for i in range(count):
        yield Chunk(index=start_index + i, text=f"Child {i}", start_char_idx=i*10, end_char_idx=(i+1)*10)

def test_uat_c02_01_single_node_refinement() -> None:
    """
    Scenario ID: UAT-C02-01 - Single Node Refinement
    Verify that the InteractiveRaptorEngine can successfully update a single node's text and metadata.
    """
    # Setup Store with a sample node
    store = DiskChunkStore()
    node = SummaryNode(
        id="node_1",
        text="Initial wisdom text.",
        level=1,
        children_indices=[0, 1],
        metadata=NodeMetadata(dikw_level=DIKWLevel.WISDOM, is_user_edited=False),
    )
    store.add_summary(node)

    # Add children chunks using generator
    store.add_chunks(chunk_generator(0, 2))

    # Setup Mock Agent
    mock_agent = MagicMock()
    # Mock summarize to return specific text
    mock_agent.summarize.return_value = "Refined wisdom text."

    # Initialize Engine
    config = ProcessingConfig(max_instruction_length=1000)
    engine = InteractiveRaptorEngine(store=store, summarizer=mock_agent, config=config)

    # Execute Refinement
    updated_node = engine.refine_node(node_id="node_1", instruction="Make it more concise")

    # Verification of returned object
    assert updated_node.text == "Refined wisdom text."
    assert isinstance(updated_node.metadata, NodeMetadata)
    assert updated_node.metadata.is_user_edited is True
    assert "Make it more concise" in updated_node.metadata.refinement_history

    # Verify persistence
    persisted_node = store.get_node("node_1")
    assert persisted_node is not None
    assert persisted_node.text == "Refined wisdom text."
    assert isinstance(persisted_node, SummaryNode)
    assert isinstance(persisted_node.metadata, NodeMetadata)
    assert persisted_node.metadata.is_user_edited is True
    assert "Make it more concise" in persisted_node.metadata.refinement_history


def test_uat_c02_02_concurrency() -> None:
    """
    Scenario ID: UAT-C02-02 - Concurrency & Persistence
    Verify that the database supports concurrent read/write operations without locking.
    """
    store = DiskChunkStore()
    node = SummaryNode(
        id="concurrent_node",
        text="Initial text",
        level=1,
        children_indices=[],
        metadata=NodeMetadata(dikw_level=DIKWLevel.DATA),
    )
    store.add_summary(node)

    stop_event = threading.Event()
    errors = []

    def reader_task() -> None:
        while not stop_event.is_set():
            try:
                # Use batch get_nodes even for single ID if we want to test streaming/performance
                # But here we test simple access.
                # Let's assume we want to read it.
                n = store.get_node("concurrent_node")
                if n is None:
                    errors.append("Node not found during read")
            except Exception as e:
                errors.append(f"Reader error: {e}")
            time.sleep(0.005)

    def writer_task() -> None:
        counter = 0
        while not stop_event.is_set():
            try:
                # Update text
                new_text = f"Updated text {counter}"
                updated_node = SummaryNode(
                    id="concurrent_node",
                    text=new_text,
                    level=1,
                    children_indices=[],
                    metadata=NodeMetadata(dikw_level=DIKWLevel.DATA),
                )
                store.update_node(updated_node)
                counter += 1
            except Exception as e:
                errors.append(f"Writer error: {e}")
            time.sleep(0.01)

    reader = threading.Thread(target=reader_task)
    writer = threading.Thread(target=writer_task)

    reader.start()
    writer.start()

    time.sleep(2)  # Run for 2 seconds
    stop_event.set()

    reader.join()
    writer.join()

    assert not errors, f"Concurrency errors occurred: {errors}"

    # Final verification: Node should be updated
    final_node = store.get_node("concurrent_node")
    assert final_node is not None
    assert final_node.text.startswith("Updated text") or final_node.text == "Initial text"

    assert final_node.text != "Initial text", "Node was not updated"
