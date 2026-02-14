import pytest
from unittest.mock import MagicMock, patch
from domain_models.config import ProcessingConfig
from matome.engines.token_chunker import JapaneseTokenChunker, TokenChunker

@pytest.fixture
def config() -> ProcessingConfig:
    return ProcessingConfig(max_tokens=10, overlap=0)

def test_token_chunker_basic(config: ProcessingConfig) -> None:
    chunker = TokenChunker()
    # "hello world" is 2 tokens in cl100k_base
    text = "hello world " * 5 # 10 tokens
    chunks = list(chunker.split_text(text, config))
    assert len(chunks) >= 1
    assert chunks[0].index == 0

def test_token_chunker_stream(config: ProcessingConfig) -> None:
    chunker = TokenChunker()
    stream = ["hello ", "world"]
    chunks = list(chunker.split_text(stream, config))
    assert len(chunks) > 0
    assert "hello" in chunks[0].text

def test_japanese_chunker_init() -> None:
    # Mock spacy load
    with patch("spacy.load") as mock_load:
        chunker = JapaneseTokenChunker()
        mock_load.assert_called()
        assert chunker.nlp is not None

def test_japanese_chunker_count_tokens() -> None:
    # Mock spacy nlp
    with patch("spacy.load") as mock_load:
        mock_nlp = MagicMock()
        mock_nlp.return_value = ["t1", "t2", "t3"] # 3 tokens
        mock_load.return_value = mock_nlp

        chunker = JapaneseTokenChunker()
        count = chunker.count_tokens("test")
        assert count == 3

def test_japanese_chunker_split(config: ProcessingConfig) -> None:
    # Mock spacy nlp pipe
    with patch("spacy.load") as mock_load:
        mock_nlp = MagicMock()

        # Mock docs and sentences
        doc1 = MagicMock()
        sent1 = MagicMock()
        sent1.text = "Sent1."
        sent1.__len__ = lambda x: 5
        doc1.sents = [sent1]

        mock_nlp.pipe.return_value = [doc1]
        mock_load.return_value = mock_nlp

        chunker = JapaneseTokenChunker()
        chunks = list(chunker.split_text("Sent1.", config))

        assert len(chunks) == 1
        assert chunks[0].text == "Sent1."

def test_japanese_chunker_large_input_safe_stream(config: ProcessingConfig) -> None:
    """Test safe streaming splitting of large inputs."""
    with patch("spacy.load") as mock_load:
        mock_nlp = MagicMock()
        mock_nlp.pipe.return_value = [] # Yield nothing for simplicity, checking input transformation
        mock_load.return_value = mock_nlp

        chunker = JapaneseTokenChunker()

        # Huge string > 10000 chars
        huge_text = "a" * 25000

        # Call safe stream directly or via split_text
        streamed = list(chunker._safe_stream(huge_text))

        # Should be split into 10000 chunks: 10000, 10000, 5000
        assert len(streamed) == 3
        assert len(streamed[0]) == 10000
        assert len(streamed[1]) == 10000
        assert len(streamed[2]) == 5000
