from .manifest import (
    AIProcessingMetadata,
    DocumentContent,
    DocumentMetadataContainer,
    DocumentNode,
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
            metadata_container=DocumentMetadataContainer(
                metadata=NodeMetadata(
                    category="business", author="System", source="upload", time_axis=None
                ),
                ai_metadata=AIProcessingMetadata(chunk_id=None, chunk_index=None),
            ),
        )
