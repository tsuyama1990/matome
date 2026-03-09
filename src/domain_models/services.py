from .interfaces import AIServiceProtocol
from .manifest import AIProcessingMetadata, DocumentContent, DocumentNode, NodeMetadata, NodeStatus


class DocumentFactory:
    """Domain service responsible for creating DocumentNode entities."""

    def __init__(self, ai_service: AIServiceProtocol) -> None:
        self.ai_service = ai_service

    def create_root_node(self, node_id: str, title: str, content_text: str) -> DocumentNode:
        """Creates a properly initialized root DocumentNode."""
        summary = self.ai_service.generate_summary(content_text)

        return DocumentNode(
            id=node_id,
            parent_id=None,
            title=title,
            content=DocumentContent(summary=summary, text=content_text),
            status=NodeStatus.LOCKED,
            metadata=NodeMetadata(
                category="business", author="System", source="upload", time_axis=None
            ),
            ai_metadata=AIProcessingMetadata(chunk_id=None, chunk_index=None),
        )
