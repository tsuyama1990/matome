import argparse
import importlib
import sys
from collections.abc import Callable
from typing import Any

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


def resolve_class(import_path: str) -> Callable[..., Any]:
    """Dynamically resolves a class from a string path (e.g., 'src.module.ClassName')."""
    module_path, class_name = import_path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_path)
    except Exception as e:
        msg = f"Failed to dynamically import module {module_path}: {e}"
        raise ImportError(msg) from e

    cls = getattr(module, class_name)
    if not callable(cls):
        msg = f"Resolved object {class_name} is not callable."
        raise TypeError(msg)

    return cls  # type: ignore[no-any-return]


def init_container() -> ProductionDIContainer:
    """Initialize the configuration and dynamically bind DI container using configured paths."""
    config = PipelineConfig()

    # Resolve the factory Callables directly from the string paths in config
    # This completely decouples main.py from any concrete implementations or test mocks.
    llm_cls = resolve_class(config.llm_service_path)
    doc_cls = resolve_class(config.document_service_path)
    kg_cls = resolve_class(config.graph_service_path)
    al_cls = resolve_class(config.active_learning_service_path)

    return ProductionDIContainer(
        config=config,
        llm_gateway_factory=llm_cls,
        document_processor_factory=doc_cls,
        knowledge_graph_factory=kg_cls,
        active_learning_factory=al_cls,
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
