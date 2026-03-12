from uuid import UUID

import pytest

from src.domain_models.document import ChunkMetadata


def test_chunk_metadata_default_uuid() -> None:
    metadata = ChunkMetadata(start_index=0, end_index=10)
    assert isinstance(metadata.source_doc_id, UUID)


def test_chunk_metadata_validations() -> None:
    with pytest.raises(ValueError, match="Input should be greater than or equal to 0"):
        ChunkMetadata(start_index=-1, end_index=10)

    with pytest.raises(ValueError, match="Input should be greater than or equal to 0"):
        ChunkMetadata(start_index=0, end_index=-1)
