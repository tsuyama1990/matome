from matome.utils.text import normalize_text, split_sentences


def test_normalize_text() -> None:
    """Test text normalization (NFKC)."""
    # Full-width alpha to half-width
    text = "１２３ＡＢＣ"
    normalized = normalize_text(text)
    assert normalized == "123ABC"

def test_split_sentences_basic() -> None:
    """Test splitting by basic Japanese punctuation."""
    text = "これが一つ目。次が二つ目！そして三つ目？"
    sentences = split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "これが一つ目。"
    assert sentences[1] == "次が二つ目！"
    assert sentences[2] == "そして三つ目？"

def test_split_sentences_newlines() -> None:
    """Test splitting by newlines."""
    text = "行が変わります\n次の行です"
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert sentences[0] == "行が変わります"
    assert sentences[1] == "次の行です"

def test_split_sentences_brackets_behavior() -> None:
    """Verify behavior with brackets (Cycle 01 simple split)."""
    text = "「彼は言った。こんにちは」"
    sentences = split_sentences(text)
    assert "「彼は言った。" in sentences
