from .manifest import (
    AIProcessingMetadata,
    DocumentContent,
    DocumentNode,
    MetadataContainer,
    NodeIdentity,
    NodeMetadata,
    NodeStatus,
)


class DocumentFactory:
    """Domain service responsible for creating DocumentNode entities."""

    def __init__(self, max_content_length: int = 100000) -> None:
        self.max_content_length = max_content_length

    def create_root_node(
        self, node_id: str, title: str, content_text: str, summary: str
    ) -> DocumentNode:
        """Creates a properly initialized root DocumentNode."""
        return DocumentNode(
            identity=NodeIdentity(
                id=node_id,
                parent_id=None,
                title=title,
                status=NodeStatus.LOCKED,
            ),
            content=DocumentContent(summary=summary, text=content_text),
        )


class MetadataService:
    """Domain service responsible for managing metadata separately from nodes."""

    def __init__(self) -> None:
        self._metadata_store: dict[str, MetadataContainer] = {}

    def create_root_metadata(self, node_id: str) -> MetadataContainer:
        metadata = MetadataContainer(
            metadata=NodeMetadata(
                category="business", author="System", source="upload", time_axis=None
            ),
            ai_metadata=AIProcessingMetadata(chunk_id=None, chunk_index=None),
        )
        self._metadata_store[node_id] = metadata
        return metadata

    def get_metadata(self, node_id: str) -> MetadataContainer | None:
        return self._metadata_store.get(node_id)

    def save_metadata(self, node_id: str, metadata: MetadataContainer) -> None:
        self._metadata_store[node_id] = metadata
