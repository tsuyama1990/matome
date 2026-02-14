import threading
import time
from unittest.mock import MagicMock

import pytest
from domain_models.manifest import Chunk, NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.utils.store import DiskChunkStore


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

    # Add children chunks
    c1 = Chunk(index=0, text="Child 1", start_char_idx=0, end_char_idx=10)
    c2 = Chunk(index=1, text="Child 2", start_char_idx=11, end_char_idx=20)
    store.add_chunks([c1, c2])

    # Setup Mock Agent
    mock_agent = MagicMock()
    # Mock summarize to return specific text
    mock_agent.summarize.return_value = "Refined wisdom text."

    # Initialize Engine
    engine = InteractiveRaptorEngine(store=store, summarizer=mock_agent, config=MagicMock())

    # Execute Refinement
    updated_node = engine.refine_node(node_id="node_1", instruction="Make it more concise")

    # Verification of returned object
    assert updated_node.text == "Refined wisdom text."
    assert updated_node.metadata.is_user_edited is True
    assert "Make it more concise" in updated_node.metadata.refinement_history

    # Verify persistence
    persisted_node = store.get_node("node_1")
    assert persisted_node is not None
    assert persisted_node.text == "Refined wisdom text."
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

    def reader_task():
        while not stop_event.is_set():
            try:
                n = store.get_node("concurrent_node")
                if n is None:
                    errors.append("Node not found during read")
            except Exception as e:
                errors.append(f"Reader error: {e}")
            time.sleep(0.005)

    def writer_task():
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
    assert final_node.text.startswith("Updated text") or final_node.text == "Initial text"
    # Note: If update_node is stub (pass), text will be "Initial text".
    # If implemented, it starts with "Updated text".
    # This assertion is loose to allow test to run, but strict one would require change.
    # To prove failure, I should assert strict change.
    assert final_node.text != "Initial text", "Node was not updated (update_node is likely a stub)"
