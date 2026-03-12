import argparse
import sys

from src.container import ProductionDIContainer
from src.domain_models.config import PipelineConfig


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
    """Initialize the configuration and dynamically bind DI container using configured paths."""
    config = PipelineConfig()
    return ProductionDIContainer(
        llm_gateway_factory=ProductionDIContainer._build_llm_factory(config),
        document_processor_factory=ProductionDIContainer._build_document_factory(config),
        knowledge_graph_factory=ProductionDIContainer._build_knowledge_graph_factory(config),
        active_learning_factory=ProductionDIContainer._build_active_learning_factory(config),
        config=config,
    )


def main() -> int:
    args = parse_args()

    try:
        container = init_container()
    except Exception as e:
        sys.stderr.write(f"Failed to initialize application container: {e}\n")
        return 1

    if args.ingest:
        sys.stdout.write(f"Starting ingestion process for: {args.ingest}\n")
        try:
            from src.domain_models import GraphState

            # We call the process through the DI container interface
            initial_state = GraphState(file_path=args.ingest)
            final_state = container.document_processor.process(initial_state)
            sys.stdout.write(f"Successfully processed {len(final_state.chunks)} chunks.\n")
        except Exception as e:
            sys.stderr.write(f"Ingestion failed: {e}\n")
            return 1

    else:
        sys.stdout.write("Hello from matome! Use --help to see available commands.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
