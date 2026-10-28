import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from tests.e2e.txt2speech.conftest import FakeVoicevoxServer
from tests.support.pdf_factory import (
    Line,
    body_line,
    body_paragraph,
    build_pdf,
    footnote_line,
    page_number_line,
)

_PROJECT_ROOT_DEPTH = 3
_PROJECT_ROOT = Path(__file__).resolve().parents[_PROJECT_ROOT_DEPTH]
_FFPROBE_BIN = "/usr/bin/ffprobe"
_EXIT_OK = 0


def _run_cli(
    args: Sequence[str],
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env is not None:
        env.update(extra_env)
    cmd = [sys.executable, "-m", "src.txt2speech", *args]
    # Execute the CLI module in a real child Python process from the project root.
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _probe_mp3(path: Path) -> dict[str, Any]:
    cmd = [
        _FFPROBE_BIN,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    # Run ffprobe against a test-generated MP3 file inside tmp_path.
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
    loaded: dict[str, Any] = json.loads(proc.stdout)
    return loaded


@pytest.mark.requirement("REQ-2026-002-F12")
@pytest.mark.requirement("REQ-2026-002-F13")
def test_e23_pdf_with_outline_creates_chapter_mp3s_and_filters_noise(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E23: PDF with cover, 3 outline items, wrapped lines, and noise produces 3 MP3s."""
    pdf_path = tmp_path / "book.pdf"
    pages: list[list[Line]] = [
        # Page 1: Cover page before the first outline entry.
        [body_line("表紙のページにある書名と著者名", 0)],
        # Page 2: Chapter 1.
        [
            *body_paragraph(
                ["一章の最初の行と", "一章の途中の折り返し行と", "最後の行で用語を使う注１。"],
                start_line_index=0,
            ),
            footnote_line("注１：脚注の詳しい説明文です。"),
            page_number_line(101),
        ],
        # Page 3: Chapter 2.
        [
            *body_paragraph(
                ["二章の最初の行と", "二章の途中の折り返し行と", "最後の行で理論を使う注２。"],
                start_line_index=0,
            ),
            footnote_line("注２：二章の脚注の説明文です。"),
            page_number_line(102),
        ],
        # Page 4: Chapter 3.
        [
            *body_paragraph(
                ["三章の最初の行と", "三章の途中の折り返し行と", "結論をまとめる文です。"],
                start_line_index=0,
            ),
            footnote_line("注３：三章の脚注の説明文です。"),
            page_number_line(103),
        ],
    ]
    outline = [
        (1, "第 1 章 序論", 2),
        (1, "第 2 章 本論", 3),
        (1, "第 3 章 結論 \uff00\u2000", 4),
    ]
    build_pdf(pdf_path, pages=pages, outline=outline)
    out_dir = tmp_path / "out"

    result = _run_cli([str(pdf_path), "-o", str(out_dir), "--engine-url", fake_voicevox.url])

    assert result.returncode == _EXIT_OK
    expected_files = [
        out_dir / "01_第1章序論.mp3",
        out_dir / "02_第2章本論.mp3",
        out_dir / "03_第3章結論.mp3",
    ]
    assert all(p.is_file() for p in expected_files)
    assert result.stdout.splitlines() == [str(p) for p in expected_files]

    assert fake_voicevox.synthesized_texts == [
        "一章の最初の行と一章の途中の折り返し行と最後の行で用語を使う。",
        "二章の最初の行と二章の途中の折り返し行と最後の行で理論を使う。",
        "三章の最初の行と三章の途中の折り返し行と結論をまとめる文です。",
    ]
    combined = "".join(fake_voicevox.synthesized_texts)
    assert "表紙のページ" not in combined
    assert "脚注の詳しい説明文" not in combined
    assert "二章の脚注" not in combined
    assert "三章の脚注" not in combined
    assert "101" not in combined
    assert "102" not in combined
    assert "103" not in combined
    assert "注１" not in combined
    assert "注２" not in combined

    expected_titles = ["第1章序論", "第2章本論", "第3章結論"]
    for mp3_path, expected_title in zip(expected_files, expected_titles, strict=True):
        probe = _probe_mp3(mp3_path)
        tags = {k.lower(): v for k, v in probe["format"]["tags"].items()}
        assert tags["title"] == expected_title


@pytest.mark.requirement("REQ-2026-002-F12")
def test_e24_pdf_without_outline_creates_single_mp3(
    tmp_path: Path,
    fake_voicevox: FakeVoicevoxServer,
) -> None:
    """T2S-E24: PDF without an outline produces 1 MP3 titled from PDF title or input stem."""
    untitled_pdf = tmp_path / "single_book.pdf"
    build_pdf(
        untitled_pdf,
        pages=[
            [
                *body_paragraph(
                    ["しおりのない文書の最初の行と", "二行目と", "三行目の文です。"],
                    start_line_index=0,
                )
            ]
        ],
        outline=[],
        title=None,
    )
    out_untitled = tmp_path / "out_untitled"

    res_untitled = _run_cli(
        [str(untitled_pdf), "-o", str(out_untitled), "--engine-url", fake_voicevox.url]
    )

    assert res_untitled.returncode == _EXIT_OK
    mp3_untitled = out_untitled / "01_single_book.mp3"
    assert mp3_untitled.is_file()
    assert res_untitled.stdout.splitlines() == [str(mp3_untitled)]
    tags_untitled = {k.lower(): v for k, v in _probe_mp3(mp3_untitled)["format"]["tags"].items()}
    assert tags_untitled["title"] == "single_book"

    titled_pdf = tmp_path / "file_name.pdf"
    build_pdf(
        titled_pdf,
        pages=[
            [
                *body_paragraph(
                    ["メタデータの題名を持つ最初の行と", "二行目の文です。"],
                    start_line_index=0,
                )
            ]
        ],
        outline=[],
        title="PDFのタイトル",
    )
    out_titled = tmp_path / "out_titled"

    res_titled = _run_cli(
        [str(titled_pdf), "-o", str(out_titled), "--engine-url", fake_voicevox.url]
    )

    assert res_titled.returncode == _EXIT_OK
    mp3_titled = out_titled / "01_PDFのタイトル.mp3"
    assert mp3_titled.is_file()
    tags_titled = {k.lower(): v for k, v in _probe_mp3(mp3_titled)["format"]["tags"].items()}
    assert tags_titled["title"] == "PDFのタイトル"
