import random

import pytest

from src.txt2speech.chunking import halve, split_chunks
from src.txt2speech.models import Chunk

_ALPHABET = "漢字語あいうえおアイウエオABC123。！？、，,「」"


def _make_random_paragraphs(rng: random.Random) -> list[str]:
    num_paragraphs = rng.randint(1, 3)
    paragraphs: list[str] = []
    for _ in range(num_paragraphs):
        length = rng.randint(1, 200)
        para = "".join(rng.choices(_ALPHABET, k=length)).strip()
        if para:
            paragraphs.append(para)
    return paragraphs or ["あ"]


def _reconstruct_paragraphs(chunks: list[Chunk]) -> list[str]:
    reconstructed: list[str] = []
    current: list[str] = []
    for chunk in chunks:
        current.append(chunk.text)
        if chunk.boundary == "paragraph":
            reconstructed.append("".join(current))
            current = []
    return reconstructed


@pytest.mark.requirement("REQ-2026-002-F05")
def test_split_chunks_paragraphs_sentences_and_commas() -> None:
    """T2S-U11: split_chunks splits by paragraph, sentence, and comma with matching boundaries."""
    para1 = "一文目です。二文目です。三文目です。"
    para2 = "これは長い文で、読点があり、さらに続きます。最後の文。"
    body = f"{para1}\n\n{para2}"

    chunks = split_chunks(body, max_chars=15)
    assert chunks == [
        Chunk(text="一文目です。", boundary="sentence"),
        Chunk(text="二文目です。", boundary="sentence"),
        Chunk(text="三文目です。", boundary="paragraph"),
        Chunk(text="これは長い文で、読点があり、", boundary="comma"),
        Chunk(text="さらに続きます。", boundary="sentence"),
        Chunk(text="最後の文。", boundary="paragraph"),
    ]


@pytest.mark.requirement("REQ-2026-002-F05")
def test_split_chunks_forced_split_and_char_class_boundary() -> None:
    """T2S-U12: split_chunks forces splits at char-class transitions or max_chars when uniform."""
    kanji_200 = "漢" * 200
    assert split_chunks(kanji_200, max_chars=80) == [
        Chunk(text="漢" * 80, boundary="other"),
        Chunk(text="漢" * 80, boundary="other"),
        Chunk(text="漢" * 40, boundary="paragraph"),
    ]

    mixed = "あ" * 70 + "情報通信技術" + "です"
    assert split_chunks(mixed, max_chars=75) == [
        Chunk(text="あ" * 70, boundary="other"),
        Chunk(text="情報通信技術です", boundary="paragraph"),
    ]

    no_punct_120 = ("あいうえお漢字カタカナABCD" * 8)[:120]
    chunks_120 = split_chunks(no_punct_120, max_chars=80)
    assert all(1 <= len(c.text) <= 80 for c in chunks_120)
    assert chunks_120[0].boundary == "other"
    assert chunks_120[-1].boundary == "paragraph"
    assert "".join(c.text for c in chunks_120) == no_punct_120


@pytest.mark.requirement("REQ-2026-002-F05")
def test_split_chunks_random_property_guarantees() -> None:
    """T2S-U13: split_chunks guarantees 1..max_chars length and lossless paragraph round-trip."""
    rng = random.Random(42)  # noqa: S311
    for _ in range(100):
        max_chars = rng.randint(5, 80)
        paragraphs = _make_random_paragraphs(rng)
        body = "\n\n".join(f"  {p}  " for p in paragraphs)

        chunks = split_chunks(body, max_chars=max_chars)
        assert len(chunks) >= len(paragraphs)
        for chunk in chunks:
            assert 1 <= len(chunk.text) <= max_chars

        assert _reconstruct_paragraphs(chunks) == paragraphs


@pytest.mark.requirement("REQ-2026-002-F05")
def test_split_chunks_closing_brackets_and_repeated_punctuation() -> None:
    """T2S-U14: split_chunks keeps closing brackets and consecutive punctuation with sentence."""
    quoted = "「はい。」と言った。"
    assert split_chunks(quoted, max_chars=80) == [
        Chunk(text="「はい。」", boundary="sentence"),
        Chunk(text="と言った。", boundary="paragraph"),
    ]

    multi_punct = "本当か？！次の文。"
    assert split_chunks(multi_punct, max_chars=80) == [
        Chunk(text="本当か？！", boundary="sentence"),
        Chunk(text="次の文。", boundary="paragraph"),
    ]
    assert split_chunks("本当か？！", max_chars=80) == [
        Chunk(text="本当か？！", boundary="paragraph"),
    ]


@pytest.mark.requirement("REQ-2026-002-F06")
def test_halve() -> None:
    """T2S-U15: halve splits at nearest char-class change, falls back to midpoint, or None."""
    near_center = "あ" * 9 + "漢字" + "あ" * 9
    assert len(near_center) == 20
    assert halve(near_center, min_chars=4) == ("あ" * 9, "漢字" + "あ" * 9)

    uniform_20 = "あ" * 20
    assert halve(uniform_20, min_chars=4) == ("あ" * 10, "あ" * 10)

    edge_only_change = "漢" + "あ" * 19
    assert halve(edge_only_change, min_chars=4) == ("漢" + "あ" * 9, "あ" * 10)

    assert halve("あ" * 7, min_chars=4) is None
