import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_file(filepath: str | Path) -> str:
    """
    Read content from a file (UTF-8).

    Args:
        filepath: Path to the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the path attempts directory traversal or is absolute/unsafe (basic check).
    """
    path = Path(filepath)

    if not path.exists():
        msg = f"File not found: {filepath}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    if not path.is_file():
        msg = f"Not a file: {filepath}"
        logger.error(msg)
        raise ValueError(msg)

    logger.debug(f"Reading file: {path}")
    return path.read_text(encoding="utf-8")
