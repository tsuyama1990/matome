import uuid
from unittest import mock

import pytest

from src.application import NLPModelLoadError, NLPService
from src.domain_models import ChunkMetadata, SemanticChunk


def test_nlp_service_load_success() -> None:
    with mock.patch("spacy.load") as mock_load:
        mock_load.return_value = mock.MagicMock()
        service = NLPService()
        assert service.nlp is not None


def test_nlp_service_load_import_error() -> None:
    with (
        mock.patch.dict("sys.modules", {"spacy": None}),
        pytest.raises(NLPModelLoadError, match="Spacy library is not installed."),
    ):
        NLPService()


def test_nlp_service_load_os_error() -> None:
    with (
        mock.patch("spacy.load", side_effect=OSError("model not found")),
        pytest.raises(
            NLPModelLoadError, match="Spacy model 'en_core_web_sm' is missing. Please install it."
        ),
    ):
        NLPService()


def test_nlp_service_tag_entities() -> None:
    with mock.patch("spacy.load") as mock_load:
        mock_nlp = mock.MagicMock()
        mock_doc = mock.MagicMock()

        mock_ent_org = mock.MagicMock()
        mock_ent_org.text = "Apple"
        mock_ent_org.label_ = "ORG"

        mock_ent_date = mock.MagicMock()
        mock_ent_date.text = "today"
        mock_ent_date.label_ = "DATE"

        mock_doc.ents = [mock_ent_org, mock_ent_date]
        mock_nlp.return_value = mock_doc
        mock_load.return_value = mock_nlp

        service = NLPService()
        chunk = SemanticChunk(
            id=uuid.uuid4(),
            content="Apple is looking at buying U.K. startup for $1 billion today",
            embedding=[0.0] * 768,
            metadata=ChunkMetadata(source_file="test.txt"),
        )
        service.tag_entities_and_axes([chunk])

        # Only ORG is in target_labels, DATE is used for time_axis
        assert "Apple" in chunk.metadata.extracted_entities
        assert "today" not in chunk.metadata.extracted_entities
        assert chunk.metadata.actor_axis == "Detected Actor"
        assert chunk.metadata.time_axis == "Detected Time"


def test_nlp_service_tag_entities_not_loaded() -> None:
    with mock.patch("spacy.load") as mock_load:
        mock_load.return_value = mock.MagicMock()
        service = NLPService()
        service.nlp = None
        with pytest.raises(RuntimeError, match="NLP model is not loaded."):
            service.tag_entities_and_axes([])
