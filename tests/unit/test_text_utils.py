from matome.utils.text import iter_sentences, normalize_text, split_sentences


def test_iter_sentences_basic() -> None:
    """Test basic sentence iteration."""
    text = "文１。文２！文３？文４\n文５"
    sentences = list(iter_sentences(text))

    assert len(sentences) == 5
    assert sentences[0] == "文１。"
    assert sentences[1] == "文２！"
    assert sentences[2] == "文３？"
    # "文４" followed by newline
    assert sentences[3] == "文４"
    assert sentences[4] == "文５"

def test_iter_sentences_empty() -> None:
    """Test empty input."""
    assert list(iter_sentences("")) == []
    assert list(iter_sentences("   \n  ")) == []

def test_iter_sentences_edge_cases() -> None:
    """Test iter_sentences with edge cases."""
    # Ends with punctuation
    text = "文１。文２。"
    sentences = list(iter_sentences(text))
    assert len(sentences) == 2
    assert sentences[0] == "文１。"
    assert sentences[1] == "文２。"

    # Consecutive delimiters
    text_consecutive = "文１。！？\n\n文２"
    # The regex `(?<=[。！？])\s*|\n+` splits after *each* delimiter.
    # 1. Match after `。`. Remainder `！？\n\n文２`. Sentence `文１。`.
    # 2. Match after `！`. Remainder `？\n\n文２`. Sentence `！`.
    # 3. Match after `？`. Remainder `\n\n文２`. Sentence `？`.
    # 4. Match `\n+`. Sentence `文２`.
    sentences = list(iter_sentences(text_consecutive))

    # We expect 4 items because the naive regex treats consecutive punctuation as separate chunks.
    assert len(sentences) == 4
    assert sentences[0] == "文１。"
    assert sentences[1] == "！"
    assert sentences[2] == "？"
    assert sentences[3] == "文２"

    # No punctuation
    text_none = "文１文２"
    sentences = list(iter_sentences(text_none))
    assert len(sentences) == 1
    assert sentences[0] == "文１文２"

def test_split_sentences_compatibility() -> None:
    """Ensure split_sentences still works and returns list."""
    text_jp = "文A。文B。"
    sentences = split_sentences(text_jp)
    assert isinstance(sentences, list)
    assert len(sentences) == 2
    assert sentences[0] == "文A。"
    assert sentences[1] == "文B。"

def test_normalize_text() -> None:
    """Test NFKC normalization."""
    # Full-width 'Ａ' -> Half-width 'A'
    assert normalize_text("ＡＢＣ") == "ABC"
    # Katakana might stay same?
    assert normalize_text("アイウ") == "アイウ"
