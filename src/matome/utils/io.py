from pathlib import Path


def read_file(filepath: str | Path) -> str:
    """Read content from a file (UTF-8)."""
    path = Path(filepath)
    if not path.exists():
        msg = f"File not found: {filepath}"
        raise FileNotFoundError(msg)

    return path.read_text(encoding="utf-8")
