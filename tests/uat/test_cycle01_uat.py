from domain_models.config import ProcessingConfig
from matome.engines.token_chunker import JapaneseTokenChunker
from matome.utils.text import normalize_text, split_sentences


def test_uat_scenario_02_ingestion_cleaning() -> None:
    """Scenario 02: Text Ingestion & Cleaning."""
    text = "１２３ＡＢＣ"
    cleaned = normalize_text(text)
    assert cleaned == "123ABC"


def test_uat_scenario_03_sentence_splitting() -> None:
    """Scenario 03: Japanese Sentence Splitting."""
    text = "「これはテストです。」と彼は言った。次の文です！"
    sentences = split_sentences(text)

    # Ideally:
    # 1. 「これはテストです。」と彼は言った。
    # 2. 次の文です！

    # Cycle 01 spec accepts simple splitting even if it breaks inside quotes.
    # We assert that "次の文です！" is a separate sentence at the end.
    assert sentences[-1] == "次の文です！"


def test_uat_scenario_04_chunk_size() -> None:
    """Scenario 04: Chunk Size Management."""
    # Long text
    sentence = "これは長い文章のテストです。" * 10
    text = sentence * 10

    chunker = JapaneseTokenChunker()
    config = ProcessingConfig(max_tokens=50)  # Small limit to force chunking
    chunks = chunker.split_text(text, config)

    assert len(chunks) > 1
