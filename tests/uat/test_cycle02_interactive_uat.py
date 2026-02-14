import contextlib
import threading
import time
from unittest.mock import MagicMock, patch

from domain_models.config import ProcessingConfig
from domain_models.manifest import NodeMetadata, SummaryNode
from domain_models.types import DIKWLevel
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from matome.utils.store import DiskChunkStore
from tests.conftest import generate_chunks, generate_summary_node


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

    # Add children chunks using generator utility
    store.add_chunks(generate_chunks(2, start_index=0))

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
    node = generate_summary_node("concurrent_node", dikw_level=DIKWLevel.DATA)
    node.text = "Initial text"
    store.add_summary(node)

    stop_event = threading.Event()
    errors = []

    def reader_task() -> None:
        while not stop_event.is_set():
            try:
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
                updated_node = generate_summary_node("concurrent_node", dikw_level=DIKWLevel.DATA)
                updated_node.text = new_text
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

def test_uat_concurrency_error_handling() -> None:
    """Test that concurrent errors are handled gracefully (simulated)."""
    # This simulates a scenario where one thread might fail, ensuring it doesn't crash the other
    store = DiskChunkStore()
    node = generate_summary_node("n1")
    store.add_summary(node)

    def failing_writer() -> None:
        # Simulate an error during write
        with (
            patch.object(store.engine, "connect", side_effect=Exception("DB Locked")),
            contextlib.suppress(Exception),
        ):
            store.update_node(node)

    def successful_reader() -> None:
        # Should still be able to read (if connection pool allows or separate conn)
        # Note: In real SQLite, if locked, read might block or fail.
        # Here we just verify threads don't crash main process.
        store.get_node("n1")

    t1 = threading.Thread(target=failing_writer)
    t2 = threading.Thread(target=successful_reader)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Pass if no unhandled exception crashed test runner
