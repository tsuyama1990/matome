from pathlib import Path
from typing import Union

def read_file(filepath: Union[str, Path]) -> str:
    """Read content from a file (UTF-8)."""
    path = Path(filepath)
    if not path.exists():
        msg = f"File not found: {filepath}"
        raise FileNotFoundError(msg)

    return path.read_text(encoding="utf-8")
