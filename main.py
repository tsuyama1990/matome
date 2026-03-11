import argparse
import sys

from src.factory import init_container


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


def main() -> int:
    args = parse_args()

    # Initialize container and config via factory
    try:
        container = init_container()
    except Exception as e:
        sys.stderr.write(f"Failed to initialize application container: {e}\n")
        return 1

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
