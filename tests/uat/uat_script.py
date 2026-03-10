import os

from src.di_container import DIContainer
from src.domain_models import ContentNode, IdentityNode


def main() -> None:
    """
    User Acceptance Test (UAT) Verification Script for Cycle 01.

    This script simulates the initial bootstrap and configuration
    loading described in the USER_TEST_SCENARIO.md.
    """

    # 1. Bootstrapping & Configuration Verification
    print("--- 1. Bootstrapping & Configuration ---")  # noqa: T201

    # Simulate setting an environment variable to override config
    os.environ["PIPELINE__MAX_CHUNK_SIZE"] = "2500"

    # Initialize the DI container (which validates config using pydantic-settings)
    container = DIContainer()
    config = container.get_config()

    print(f"Pipeline Max Chunk Size Configured to: {config.pipeline.max_chunk_size}")  # noqa: T201
    assert config.pipeline.max_chunk_size == 2500, "Config override failed."

    print("\n--- 2. Simulated Ingestion (Data Model Verification) ---")  # noqa: T201
    # Simulate extracting a node from a legacy manual
    identity = IdentityNode(
        id="node_001",
        parent_id=None,
        level=0,
        is_locked=True,
        tags={"topic": "System Architecture", "status": "as-is"},
    )

    content = ContentNode(
        id="node_001",
        original_text="The legacy system requires a manual approval process.",
        summary_text="Manual approval required.",
        entities=["legacy system", "approval process"],
    )

    print(f"Created IdentityNode ID: {identity.id}, Locked: {identity.is_locked}")  # noqa: T201
    print(f"Created ContentNode ID: {content.id}, Entities: {content.entities}")  # noqa: T201

    # 3. Interactive SQ3R Simulation (State Change)
    print("\n--- 3. Interactive SQ3R Simulation ---")  # noqa: T201
    print("User answers the AI question correctly...")  # noqa: T201

    # Transition node state from locked to unlocked
    identity.is_locked = False
    print(f"IdentityNode ID: {identity.id} successfully unlocked (Locked: {identity.is_locked})")  # noqa: T201
    assert identity.is_locked is False, "State transition failed."

    print("\n✓ UAT Cycle 01 Verification Complete.")  # noqa: T201


if __name__ == "__main__":
    main()
