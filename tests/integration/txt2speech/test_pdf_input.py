import io
import wave
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.txt2speech.cli import EXIT_INPUT_ERROR, main
from src.txt2speech.config import Settings
from src.txt2speech.dictionary import DictEntry
from src.txt2speech.errors import EngineError, InputError
from src.txt2speech.models import Chapter
from src.txt2speech.pdf_input import read_pdf_chapters
from src.txt2speech.pipeline import run
from tests.support.pdf_factory import (
    Line,
    body_line,
    body_paragraph,
    build_pdf,
    footnote_line,
    page_number_line,
)

_WAV_RATE = 24000
_WAV_CHANNELS = 1
_WAV_SAMPWIDTH = 2
_FRAMES_PER_CHAR = 100


def _make_wav_bytes(num_frames: int = 240) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(_WAV_CHANNELS)
        writer.setsampwidth(_WAV_SAMPWIDTH)
        writer.setframerate(_WAV_RATE)
        writer.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


@dataclass(frozen=True)
class _EncodeRecord:
    wav_path: Path
    out_path: Path
    title: str
    album: str
    track: int


class _FakeEncoder:
    def __init__(self) -> None:
        self.calls: list[_EncodeRecord] = []

    def __call__(
        self,
        wav_path: Path,
        out_path: Path,
        title: str,
        album: str,
        track: int,
    ) -> None:
        assert wav_path.is_file()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"FAKE_MP3_DATA")
        self.calls.append(
            _EncodeRecord(
                wav_path=wav_path,
                out_path=out_path,
                title=title,
                album=album,
                track=track,
            )
        )


class _FakeClient:
    def __init__(self, *, crash_on_call: int | None = None) -> None:
        self.crash_on_call = crash_on_call
        self.registered: list[DictEntry] = []
        self.attempted_texts: list[str] = []
        self.synthesized_texts: list[str] = []

    def check(self) -> None:
        return None

    def register(self, entry: DictEntry) -> None:
        self.registered.append(entry)

    def synthesize(self, text: str) -> bytes:
        self.attempted_texts.append(text)
        call_no = len(self.attempted_texts)
        if self.crash_on_call is not None and call_no == self.crash_on_call:
            msg = f"simulated synthesis crash on call {call_no}"
            raise EngineError(msg)
        self.synthesized_texts.append(text)
        return _make_wav_bytes(max(1, len(text)) * _FRAMES_PER_CHAR)


@pytest.mark.requirement("REQ-2026-002-F12")
@pytest.mark.requirement("REQ-2026-002-F13")
def test_read_pdf_chapters_outline_cover_footnotes_and_paragraphs(tmp_path: Path) -> None:
    """T2S-I22: read_pdf_chapters extracts 3 chapters, skips cover/noise, and joins paragraphs."""
    pdf_path = tmp_path / "book.pdf"
    pages: list[list[Line]] = [
        # Page 1: Cover page before the first outline item.
        [body_line("表紙のタイトルと著者名", 0)],
        # Page 2: Chapter 1 page 1 (indented paragraphs, wrapped lines, footnote, page num).
        [
            *body_paragraph(
                ["第一段落の一行目と", "折り返した二行目を使う注１。"],
                start_line_index=0,
            ),
            *body_paragraph(
                ["第二段落の一行目と", "折り返した二行目です。"],
                start_line_index=2,
            ),
            footnote_line("注１：脚注の補足説明です。"),
            page_number_line(2),
        ],
        # Page 3: Chapter 1 page 2 (continues before Chapter 2 starts on page 4).
        [
            *body_paragraph(
                ["一章の二ページ目にある", "追加の段落の本文です。"],
                start_line_index=0,
            ),
            page_number_line(3),
        ],
        # Page 4: Chapter 2.
        [
            *body_paragraph(
                ["二章の最初の行と", "二行目と", "三行目の文です。"],
                start_line_index=0,
            ),
            footnote_line("注２：二章の脚注です。"),
            page_number_line(4),
        ],
        # Page 5: Chapter 3.
        [
            *body_paragraph(["三章のまとめの行と", "最後の行です。"], start_line_index=0),
            page_number_line(5),
        ],
    ]
    outline = [
        (1, "第 1 章 序論", 2),
        (1, "第 2 章 本論", 4),
        (1, "第 3 章 結論 \uff00\u2000", 5),
    ]
    build_pdf(pdf_path, pages=pages, outline=outline)

    chapters = read_pdf_chapters(pdf_path, Settings())

    assert [ch.title for ch in chapters] == ["第1章序論", "第2章本論", "第3章結論"]
    assert chapters[0].body == (
        "第一段落の一行目と折り返した二行目を使う。\n\n"
        "第二段落の一行目と折り返した二行目です。\n\n"
        "一章の二ページ目にある追加の段落の本文です。"
    )
    assert chapters[1].body == "二章の最初の行と二行目と三行目の文です。"
    assert chapters[2].body == "三章のまとめの行と最後の行です。"

    all_bodies = "\n".join(ch.body for ch in chapters)
    assert "表紙のタイトル" not in all_bodies
    assert "脚注の補足説明" not in all_bodies
    assert "二章の脚注" not in all_bodies
    assert "注１" not in all_bodies


@pytest.mark.requirement("REQ-2026-002-F12")
def test_read_pdf_chapters_levels_no_outline_same_page_and_empty_chapter(
    tmp_path: Path,
) -> None:
    """T2S-I23: read_pdf_chapters handles 2-level outlines, no outline, same-page, and empty chapters."""
    # 2-level outline, same-page duplicate, and empty chapter page.
    hierarchy_pdf = tmp_path / "hierarchy.pdf"
    pages: list[list[Line]] = [
        [*body_paragraph(["一章の導入の行と", "導入の二行目の本文です。"], start_line_index=0)],
        [*body_paragraph(["一章一節の行と", "一節の二行目の本文です。"], start_line_index=0)],
        [page_number_line(3)],  # Page 3 has only a page number -> empty body.
        [*body_paragraph(["二章の行と", "二章の二行目の本文です。"], start_line_index=0)],
    ]
    outline = [
        (1, "第 1 部", 1),
        (1, "第 1 章", 1),  # Same page as 第 1 部 -> later entry wins.
        (2, "1.1 節", 2),
        (1, "空の章", 3),  # Page 3 has no body after noise removal -> skipped.
        (1, "第 2 章", 4),
    ]
    build_pdf(hierarchy_pdf, pages=pages, outline=outline)

    level1_chapters = read_pdf_chapters(hierarchy_pdf, Settings(pdf_outline_level=1))
    assert [ch.title for ch in level1_chapters] == ["第1章", "第2章"]
    assert level1_chapters[0].body == (
        "一章の導入の行と導入の二行目の本文です。\n\n一章一節の行と一節の二行目の本文です。"
    )
    assert level1_chapters[1].body == "二章の行と二章の二行目の本文です。"

    level2_chapters = read_pdf_chapters(hierarchy_pdf, Settings(pdf_outline_level=2))
    assert [ch.title for ch in level2_chapters] == ["第1章", "1.1節", "第2章"]

    # Outline-less PDF with metadata Title uses the metadata Title.
    titled_pdf = tmp_path / "no_outline_titled.pdf"
    build_pdf(
        titled_pdf,
        pages=[
            [*body_paragraph(["しおりのない本文の一行目と", "二行目です。"], start_line_index=0)]
        ],
        outline=[],
        title="経営学入門",
    )
    assert read_pdf_chapters(titled_pdf, Settings()) == [
        Chapter(title="経営学入門", body="しおりのない本文の一行目と二行目です。")
    ]

    # Outline-less PDF without metadata Title falls back to the input filename stem.
    untitled_pdf = tmp_path / "stem_fallback.pdf"
    build_pdf(
        untitled_pdf,
        pages=[
            [*body_paragraph(["タイトルなしの本文の一行目と", "二行目です。"], start_line_index=0)]
        ],
        outline=[],
        title=None,
    )
    assert read_pdf_chapters(untitled_pdf, Settings()) == [
        Chapter(title="stem_fallback", body="タイトルなしの本文の一行目と二行目です。")
    ]


@pytest.mark.requirement("REQ-2026-002-F12")
def test_pipeline_run_with_pdf_input_and_resume(tmp_path: Path) -> None:
    """T2S-I24: pipeline.run processes PDF chapters into 01_.../02_... MP3s with resume and cleanup."""
    pdf_path = tmp_path / "course.pdf"
    pages: list[list[Line]] = [
        [*body_paragraph(["一章の一文目です。一章の二文目です。"], start_line_index=0)],
        [*body_paragraph(["二章の一文目です。二章の二文目です。"], start_line_index=0)],
    ]
    outline = [
        (1, "第 1 章", 1),
        (1, "第 2 章", 2),
    ]
    build_pdf(pdf_path, pages=pages, outline=outline)
    out_dir = tmp_path / "out"
    settings = Settings(max_chunk_chars=80)

    # First run crashes on the 4th chunk (in chapter 2) after chapter 1 completes.
    crashing_client = _FakeClient(crash_on_call=4)
    encoder_first = _FakeEncoder()
    with pytest.raises(EngineError):
        run(
            input_path=pdf_path,
            out_dir=out_dir,
            settings=settings,
            client=crashing_client,
            encoder=encoder_first,
        )

    assert (out_dir / "01_第1章.mp3").is_file()
    assert not (out_dir / "02_第2章.mp3").exists()
    assert (out_dir / settings.progress_file_name).is_file()

    # Resume completes chapter 2 without resynthesizing chapter 1 or chapter 2 chunk 1.
    resume_client = _FakeClient()
    encoder_resume = _FakeEncoder()
    mp3_paths = run(
        input_path=pdf_path,
        out_dir=out_dir,
        settings=settings,
        client=resume_client,
        encoder=encoder_resume,
    )

    assert [p.name for p in mp3_paths] == ["01_第1章.mp3", "02_第2章.mp3"]
    assert resume_client.synthesized_texts == ["二章の二文目です。"]
    assert not (out_dir / settings.work_dir_name).exists()
    assert not (out_dir / settings.progress_file_name).exists()


@pytest.mark.requirement("REQ-2026-002-F12")
def test_unreadable_broken_and_encrypted_pdfs_raise_input_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T2S-I25: Broken and password-encrypted PDFs raise InputError naming the file and exit with 2."""
    broken_pdf = tmp_path / "broken_file.pdf"
    broken_pdf.write_bytes(b"not a valid pdf file \x00\xff\xfe")

    with pytest.raises(InputError) as broken_exc:
        read_pdf_chapters(broken_pdf, Settings())
    assert broken_pdf.name in str(broken_exc.value)

    code_broken = main([str(broken_pdf), "-o", str(tmp_path / "out_broken")])
    captured_broken = capsys.readouterr()
    assert code_broken == EXIT_INPUT_ERROR
    assert broken_pdf.name in captured_broken.err

    encrypted_pdf = tmp_path / "secret_book.pdf"
    build_pdf(
        encrypted_pdf,
        pages=[[*body_paragraph(["暗号化された本文です。"], start_line_index=0)]],
        outline=[(1, "第1章", 1)],
        encrypt="pw",
    )

    with pytest.raises(InputError) as enc_exc:
        read_pdf_chapters(encrypted_pdf, Settings())
    assert encrypted_pdf.name in str(enc_exc.value)

    code_enc = main([str(encrypted_pdf), "-o", str(tmp_path / "out_enc")])
    captured_enc = capsys.readouterr()
    assert code_enc == EXIT_INPUT_ERROR
    assert encrypted_pdf.name in captured_enc.err
