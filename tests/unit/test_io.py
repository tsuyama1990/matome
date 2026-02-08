from pathlib import Path

import pytest

from matome.utils.io import read_file


def test_read_file_success(tmp_path: Path) -> None:
    """Test reading a file successfully."""
    p = tmp_path / "test.txt"
    p.write_text("content", encoding="utf-8")
    content = read_file(p)
    assert content == "content"

def test_read_file_not_found() -> None:
    """Test reading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_file("non_existent_file.txt")

def test_read_file_is_directory(tmp_path: Path) -> None:
    """Test reading a directory raises ValueError."""
    # tmp_path is a directory
    with pytest.raises(ValueError, match="Not a file"):
        read_file(tmp_path)
