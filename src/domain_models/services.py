from .interfaces import MetadataRepository
from .manifest import (
    AIMetadataContainer,
    AIProcessingMetadata,
    Content,
    ContentNode,
    IdentityNode,
    NodeMetadata,
    NodeMetadataContainer,
    NodeStatus,
)


class DocumentFactory:
    """Domain service responsible for creating decoupled Identity and Content entities."""

    def __init__(self, max_content_length: int) -> None:
        self.max_content_length = max_content_length

    def create_root_node(
        self, node_id: str, title: str, content_text: str, summary: str
    ) -> tuple[IdentityNode, ContentNode]:
        """Creates correctly isolated identity and content structures."""

        identity = IdentityNode(id=node_id, parent_id=None, title=title, status=NodeStatus.LOCKED)
        content = ContentNode(node_id=node_id, content=Content(summary=summary, text=content_text))
        return identity, content


class MetadataService:
    """Domain service responsible for managing metadata separately from nodes using an injected repository."""

    def __init__(self, repository: MetadataRepository) -> None:
        self.repository = repository

    def create_root_metadata(
        self, node_id: str
    ) -> tuple[NodeMetadataContainer, AIMetadataContainer]:
        node_metadata = NodeMetadataContainer(
            node_id=node_id,
            metadata=NodeMetadata(
                category="business", author="System", source="upload", time_axis=None
            ),
        )
        ai_metadata = AIMetadataContainer(
            node_id=node_id,
            ai_metadata=AIProcessingMetadata(chunk_id=None, chunk_index=None),
        )
        self.repository.save_node_metadata(node_metadata)
        self.repository.save_ai_metadata(ai_metadata)
        return node_metadata, ai_metadata

    def get_node_metadata(self, node_id: str) -> NodeMetadataContainer | None:
        return self.repository.get_node_metadata(node_id)

    def get_ai_metadata(self, node_id: str) -> AIMetadataContainer | None:
        return self.repository.get_ai_metadata(node_id)

    def save_node_metadata(self, metadata: NodeMetadataContainer) -> None:
        self.repository.save_node_metadata(metadata)

    def save_ai_metadata(self, metadata: AIMetadataContainer) -> None:
        self.repository.save_ai_metadata(metadata)
