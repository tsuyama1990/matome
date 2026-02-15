import logging
from collections import deque
from collections.abc import Iterator

from domain_models.constants import DEFAULT_TRAVERSAL_MAX_QUEUE_SIZE
from domain_models.manifest import Chunk, SummaryNode
from matome.exceptions import StoreError
from matome.utils.store import DiskChunkStore

logger = logging.getLogger(__name__)


def traverse_source_chunks(
    store: DiskChunkStore,
    root: SummaryNode,
    limit: int | None = None,
    max_queue_size: int = DEFAULT_TRAVERSAL_MAX_QUEUE_SIZE,
) -> Iterator[Chunk]:
    """
    Traverse source chunks using layer-by-layer BFS with batch fetching.
    Reduces N+1 queries by fetching children of the entire current layer at once.
    """
    queue: deque[SummaryNode] = deque([root])
    visited: set[str] = {str(root.id)}
    yielded_count = 0

    while queue:
        if limit and yielded_count >= limit:
            break

        current_layer_nodes = list(queue)
        queue.clear()

        # Collect all child IDs for this layer
        all_child_ids = _collect_child_ids(current_layer_nodes)
        if not all_child_ids:
            continue

        try:
            # Batch fetch and process children
            children_iter = store.get_nodes(all_child_ids)
            for child in children_iter:
                if isinstance(child, Chunk):
                    yield child
                    yielded_count += 1
                    if limit and yielded_count >= limit:
                        return
                elif isinstance(child, SummaryNode) and str(child.id) not in visited:
                    visited.add(str(child.id))
                    if len(queue) < max_queue_size:
                        queue.append(child)
                    else:
                        logger.warning("Traversal queue limit reached. Truncating search.")
        except (StoreError, ValueError):
            logger.exception("Error during source chunk traversal")
            break


def _collect_child_ids(nodes: list[SummaryNode]) -> list[str | int]:
    """Collect all child IDs from a list of nodes."""
    ids: list[str | int] = []
    for node in nodes:
        ids.extend(node.children_indices)
    return ids
