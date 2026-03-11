import argparse
import sys

from src.container import ProductionDIContainer
from src.domain_models.config import PipelineConfig

# We will need to stub out dummy implementations to make main functional,
# although we expect the real implementations to be built in later cycles.
from tests.unit.test_container import (
    MockActiveLearningService,
    MockDocumentProcessingService,
    MockKnowledgeGraphService,
    MockLLMProtocol,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="matome: Interactive active learning and knowledge extraction platform"
    )
    parser.add_argument(
        "--ingest",
        type=str,
        help="Path to the document to ingest and analyze",
        required=False,
    )
    return parser.parse_args()


def init_container() -> ProductionDIContainer:
    """Initialize the configuration and DI container for the application."""
    try:
        config = PipelineConfig()

        # In a real cycle 02/03 implementation we inject the concrete classes here.
        # For now, we inject robust mocks from the test suite to satisfy DI validation.
        llm = MockLLMProtocol()
        doc = MockDocumentProcessingService()
        kg = MockKnowledgeGraphService()
        al = MockActiveLearningService()

        return ProductionDIContainer(
            config=config,
            llm_gateway=llm,
            document_processor=doc,
            knowledge_graph=kg,
            active_learning=al,
        )
    except Exception as e:
        sys.stderr.write(f"Failed to initialize application container: {e}\n")
        sys.exit(1)


def main() -> int:
    args = parse_args()

    # Initialize container and config
    container = init_container()

    if args.ingest:
        sys.stdout.write(f"Starting ingestion process for: {args.ingest}\n")
        try:
            # We call the process through the DI container interface
            container.document_processor.process(args.ingest)
        except Exception as e:
            sys.stderr.write(f"Ingestion failed: {e}\n")
            return 1

    else:
        sys.stdout.write("Hello from matome! Use --help to see available commands.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
