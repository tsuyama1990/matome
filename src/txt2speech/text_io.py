from pathlib import Path

from src.txt2speech.errors import InputError

# Try UTF-8 (with optional BOM stripped via utf-8-sig) before falling back to CP932.
_CANDIDATE_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "cp932")


def read_text(path: Path) -> str:
    if not path.is_file():
        msg = f"入力ファイルが見つかりません: {path}"
        raise InputError(msg)

    try:
        raw = path.read_bytes()
    except OSError as exc:
        msg = f"入力ファイルの読み込みに失敗しました: {path}"
        raise InputError(msg) from exc

    for encoding in _CANDIDATE_ENCODINGS:
        try:
            decoded = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        return decoded

    msg = f"文字コードを判別できません (UTF-8/CP932): {path}"
    raise InputError(msg)
