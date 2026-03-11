import argparse
import sys

from src.container import ProductionDIContainer


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
    # ProductionDIContainer now self-resolves components via registry mapping to Config safely.
    return ProductionDIContainer()


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
